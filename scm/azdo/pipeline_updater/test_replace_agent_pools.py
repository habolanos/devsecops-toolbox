"""
Tests para options.replace_agent_pools con filtro de stages.

Cubre:
- Parsing del formato plano (backward compatible)
- Parsing del formato estructurado (mappings + stages)
- Normalizacion de criterios name/pattern y strings
- Validacion fail-fast de regex invalidos
- Reemplazo en todos los stages (sin filtro)
- Reemplazo solo en stages filtrados por name y pattern
- Actualizacion del objeto queue.id cuando existe
"""

import unittest
from .template_parser import TemplateParser
from .update_engine import UpdateEngine
from .models import TemplateOptions, ReplaceAgentPools


def make_options(raw) -> TemplateOptions:
    """Construir TemplateOptions simulando el parseo de un template."""
    parser = TemplateParser.__new__(TemplateParser)
    parser.template = {}
    parser.metadata = {}
    parser.search_rules = {}
    parser.update_rules = {}
    parser.options = {'replace_agent_pools': raw}
    return parser.get_template_options()


def make_definition() -> dict:
    """Definicion con 4 environments, cada uno con deployPhases y queueId."""
    def env(env_id, name, queue_id):
        return {
            'id': env_id,
            'name': name,
            'rank': env_id,
            'deployPhases': [{
                'deploymentInput': {
                    'queueId': queue_id,
                    'queue': {'id': queue_id, 'name': 'pool-viejo'}
                }
            }]
        }

    return {
        'id': 300,
        'name': 'Pipeline Test Agent Pools',
        'environments': [
            env(1, 'Develop', 1749),
            env(2, 'QA', 1751),
            env(3, '01-Culiacan', 2722),
            env(4, 'Production', 9000),
        ],
        'artifacts': [],
        'triggers': [],
    }


def queue_ids(definition) -> dict:
    """queueId actual por nombre de environment."""
    return {
        e['name']: e['deployPhases'][0]['deploymentInput']['queueId']
        for e in definition['environments']
    }


class TestReplaceAgentPoolsParser(unittest.TestCase):
    """Tests de parsing de options.replace_agent_pools."""

    def test_flat_format_backward_compatible(self):
        opts = make_options({1749: 5331, 1751: 5331})
        pools = opts.replace_agent_pools
        self.assertTrue(pools.has_any())
        self.assertEqual(pools.mappings, {1749: 5331, 1751: 5331})
        self.assertEqual(pools.stage_filters, [])

    def test_structured_format_parses_mappings_and_stages(self):
        opts = make_options({
            'stages': [{'name': 'QA'}, {'pattern': r'^\d{2}-'}],
            'mappings': {1749: 5331}
        })
        pools = opts.replace_agent_pools
        self.assertEqual(pools.mappings, {1749: 5331})
        self.assertEqual(pools.stage_filters,
                         [{'name': 'QA'}, {'pattern': r'^\d{2}-'}])

    def test_structured_format_without_stages(self):
        opts = make_options({'mappings': {2722: 5331}})
        pools = opts.replace_agent_pools
        self.assertEqual(pools.mappings, {2722: 5331})
        self.assertEqual(pools.stage_filters, [])

    def test_string_stage_normalizes_to_name(self):
        opts = make_options({
            'stages': ['QA', 'Production'],
            'mappings': {1749: 5331}
        })
        self.assertEqual(opts.replace_agent_pools.stage_filters,
                         [{'name': 'QA'}, {'name': 'Production'}])

    def test_invalid_regex_raises(self):
        with self.assertRaises(ValueError):
            make_options({
                'stages': [{'pattern': '([invalid'}],
                'mappings': {1749: 5331}
            })

    def test_empty_or_none_returns_empty(self):
        self.assertFalse(make_options(None).replace_agent_pools.has_any())
        self.assertFalse(make_options({}).replace_agent_pools.has_any())


class TestReplaceAgentPoolsEngine(unittest.TestCase):
    """Tests del engine: reemplazo global y filtrado por stage."""

    def run_engine(self, definition, options):
        engine = UpdateEngine(definition, [], {}, options)
        self.assertTrue(engine.apply_updates())
        return engine

    def test_flat_format_replaces_all_matching_stages(self):
        definition = make_definition()
        engine = self.run_engine(
            definition,
            make_options({1749: 5331, 1751: 5331, 2722: 5331, 9000: 5331}))

        self.assertEqual(queue_ids(definition), {
            'Develop': 5331, 'QA': 5331,
            '01-Culiacan': 5331, 'Production': 5331
        })
        self.assertEqual(len([
            c for c in engine.changes
            if c['type'] == 'agent_pool_replaced'
        ]), 4)

    def test_unmapped_queue_id_not_replaced(self):
        definition = make_definition()
        self.run_engine(definition, make_options({1749: 5331}))

        qids = queue_ids(definition)
        self.assertEqual(qids['Develop'], 5331)
        self.assertEqual(qids['QA'], 1751)          # sin cambios
        self.assertEqual(qids['01-Culiacan'], 2722)  # sin cambios

    def test_name_filter_scopes_replacement(self):
        definition = make_definition()
        self.run_engine(definition, make_options({
            'stages': [{'name': 'QA'}],
            'mappings': {1751: 5331, 1749: 5331, 2722: 5331}
        }))

        qids = queue_ids(definition)
        self.assertEqual(qids['QA'], 5331)
        self.assertEqual(qids['Develop'], 1749)
        self.assertEqual(qids['01-Culiacan'], 2722)

    def test_pattern_filter_scopes_replacement(self):
        definition = make_definition()
        self.run_engine(definition, make_options({
            'stages': [{'pattern': r'^\d{2}-'}],
            'mappings': {2722: 5331, 1749: 5331}
        }))

        qids = queue_ids(definition)
        self.assertEqual(qids['01-Culiacan'], 5331)
        self.assertEqual(qids['Develop'], 1749)
        self.assertEqual(qids['QA'], 1751)

    def test_mixed_name_and_pattern_filters(self):
        definition = make_definition()
        self.run_engine(definition, make_options({
            'stages': [{'name': 'QA'}, {'pattern': r'^\d{2}-'}],
            'mappings': {1751: 5331, 2722: 5331}
        }))

        qids = queue_ids(definition)
        self.assertEqual(qids['QA'], 5331)
        self.assertEqual(qids['01-Culiacan'], 5331)
        self.assertEqual(qids['Develop'], 1749)
        self.assertEqual(qids['Production'], 9000)

    def test_name_wildcard_filter(self):
        definition = make_definition()
        self.run_engine(definition, make_options({
            'stages': [{'name': 'Prod*'}],
            'mappings': {9000: 5331}
        }))
        self.assertEqual(queue_ids(definition)['Production'], 5331)

    def test_filter_matching_nothing_produces_no_changes(self):
        definition = make_definition()
        engine = self.run_engine(definition, make_options({
            'stages': [{'name': 'NoExiste'}],
            'mappings': {1749: 5331}
        }))
        self.assertEqual(engine.changes, [])
        self.assertEqual(queue_ids(definition)['Develop'], 1749)

    def test_queue_object_id_updated(self):
        definition = make_definition()
        self.run_engine(definition, make_options({1749: 5331}))

        queue_obj = (definition['environments'][0]
                     ['deployPhases'][0]['deploymentInput']['queue'])
        self.assertEqual(queue_obj['id'], 5331)

    def test_empty_mappings_is_noop(self):
        definition = make_definition()
        engine = self.run_engine(definition, TemplateOptions())
        self.assertEqual(engine.changes, [])


if __name__ == '__main__':
    unittest.main()
