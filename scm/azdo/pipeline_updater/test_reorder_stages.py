"""
Tests para el reordenamiento de stages en UpdateEngine.

Verifican que el campo 'rank' de cada environment se actualice correctamente,
ya que en Azure DevOps el orden lo determina 'rank' y no la posición en el array.
"""

import unittest

from .update_engine import UpdateEngine


class TestReorderStages(unittest.TestCase):
    """Tests para _reorder_stages"""

    def setUp(self):
        # Orden original (ranks): QA=1, Staging=2, Production=3, Develop=4
        self.definition = {
            'environments': [
                {'id': 12578, 'name': 'QA', 'rank': 1},
                {'id': 12579, 'name': 'Production', 'rank': 3},
                {'id': 12580, 'name': 'Staging', 'rank': 2},
                {'id': 16842, 'name': 'Develop', 'rank': 4},
            ]
        }
        # Nuevo orden deseado: Develop=1, QA=2, Staging=3, Production=4
        self.update_rules = {
            'stages': [
                {'name': 'Develop', 'rank': 1},
                {'name': 'QA', 'rank': 2},
                {'name': 'Staging', 'rank': 3},
                {'name': 'Production', 'rank': 4},
            ]
        }

    def _ranks_by_name(self):
        return {e['name']: e['rank'] for e in self.definition['environments']}

    def test_ranks_updated(self):
        """Cada environment debe recibir el rank definido en el template."""
        engine = UpdateEngine(self.definition, [], self.update_rules)
        engine.apply_updates()

        ranks = self._ranks_by_name()
        self.assertEqual(ranks['Develop'], 1)
        self.assertEqual(ranks['QA'], 2)
        self.assertEqual(ranks['Staging'], 3)
        self.assertEqual(ranks['Production'], 4)

    def test_array_reordered_by_rank(self):
        """El array de environments debe quedar ordenado por el nuevo rank."""
        engine = UpdateEngine(self.definition, [], self.update_rules)
        engine.apply_updates()

        names_in_order = [e['name'] for e in self.definition['environments']]
        self.assertEqual(names_in_order, ['Develop', 'QA', 'Staging', 'Production'])

    def test_changes_recorded(self):
        """Se deben registrar los cambios con old_rank y new_rank."""
        engine = UpdateEngine(self.definition, [], self.update_rules)
        engine.apply_updates()

        changes = engine.get_changes()
        self.assertEqual(len(changes), 4)
        for change in changes:
            self.assertEqual(change['type'], 'stage_reorder')
            self.assertIn('old_rank', change)
            self.assertIn('new_rank', change)

    def test_ranks_are_unique_permutation(self):
        """Los ranks resultantes deben ser una permutación única 1..N."""
        engine = UpdateEngine(self.definition, [], self.update_rules)
        engine.apply_updates()

        ranks = sorted(self._ranks_by_name().values())
        self.assertEqual(ranks, [1, 2, 3, 4])


if __name__ == '__main__':
    unittest.main()
