# -*- coding: utf-8 -*-
"""Tests unitarios de azdo_permission_audit (opción 49)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "azdo"))
import azdo_permission_audit as pv  # noqa: E402


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════
ACTIONS_REL = {1: "ViewReleaseDefinition", 2: "EditReleaseDefinition",
               4: "DeleteReleaseDefinition", 128: "ManageReleases",
               8192: "AdministerReleasePermissions"}
ACTIONS_BUILD = {1: "ViewBuildDefinition", 2: "EditBuildDefinition",
                 16: "QueueBuilds", 8192: "AdministerBuildPermissions"}
ACTIONS_GIT = {1: "Read", 2: "Contribute", 8: "ForcePush",
               32768: "ManagePermissions"}


def _user(desc="aad.u1", name="Ana", mail="ana@x.com"):
    return pv.Identity(desc, "user", name, mail, desc)


# ═════════════════════════════════════════════════════════════════════════════
# Decodificación de bits / helpers puros
# ═════════════════════════════════════════════════════════════════════════════
def test_decode_bits():
    assert pv.decode_bits(3, ACTIONS_REL) == [
        "ViewReleaseDefinition", "EditReleaseDefinition"]
    assert pv.decode_bits(128, ACTIONS_REL) == ["ManageReleases"]
    assert pv.decode_bits(0, ACTIONS_REL) == []


def test_bit_positions():
    assert pv._bit_positions(6) == [2, 4]
    assert pv._bit_positions(8192) == [8192]


def test_is_sensitive():
    assert pv.is_sensitive("EditReleaseDefinition") is True
    assert pv.is_sensitive("ManageReleases") is True
    assert pv.is_sensitive("AdministerReleasePermissions") is True
    assert pv.is_sensitive("ForcePush") is True
    assert pv.is_sensitive("ViewReleaseDefinition") is False
    assert pv.is_sensitive("Read") is False


def test_ace_bits_extended():
    ace = {"allow": 1, "deny": 0,
           "extendedInfo": {"effectiveAllow": 3, "effectiveDeny": 0}}
    assert pv.ace_bits(ace) == (3, 0)
    assert pv.ace_bits({"allow": 5, "deny": 2}) == (5, 2)


def test_aces_to_subjects_merge():
    """Dos identityDescriptors del mismo sujeto se unen."""
    aces = {"id1": {"allow": 1, "deny": 0},
            "id2": {"allow": 2, "deny": 0},
            "id3": {"allow": 4, "deny": 0}}
    sub = {"id1": "vssgp.g", "id2": "vssgp.g", "id3": "aad.u"}
    out = pv.aces_to_subjects(aces, sub)
    assert set(out) == {"vssgp.g", "aad.u"}
    a, _ = pv.ace_bits(out["vssgp.g"])
    assert a == 3
    a2, _ = pv.ace_bits(out["aad.u"])
    assert a2 == 4


# ═════════════════════════════════════════════════════════════════════════════
# Matriz efectiva: directo + heredado + deny
# ═════════════════════════════════════════════════════════════════════════════
def test_effective_directa():
    aces = {"aad.u1": {"allow": 2, "deny": 0}}
    gou = {"aad.u1": set()}
    out = pv.build_effective_map(aces, gou, {}, ACTIONS_REL)
    assert out["aad.u1"] == {2: "directa"}


def test_effective_heredada_grupo():
    """El usuario no tiene ACE pero su grupo sí → hereda con origen
    'grupo:<nombre>'."""
    aces = {"vssgp.devs": {"allow": 2, "deny": 0}}
    gou = {"aad.u1": {"vssgp.devs"}}
    gnames = {"vssgp.devs": "Dev Team"}
    out = pv.build_effective_map(aces, gou, gnames, ACTIONS_REL)
    assert out["aad.u1"] == {2: "grupo:Dev Team"}


def test_effective_directa_y_grupo():
    aces = {"aad.u1": {"allow": 1, "deny": 0},
            "vssgp.devs": {"allow": 2, "deny": 0}}
    gou = {"aad.u1": {"vssgp.devs"}}
    out = pv.build_effective_map(aces, gou,
                                 {"vssgp.devs": "Dev"}, ACTIONS_REL)
    assert out["aad.u1"][1] == "directa"
    assert out["aad.u1"][2] == "grupo:Dev"


def test_effective_deny_precede():
    """deny de cualquier ACE elimina el bit aunque otro lo permita."""
    aces = {"aad.u1": {"allow": 7, "deny": 0},
            "vssgp.devs": {"allow": 0, "deny": 2}}
    gou = {"aad.u1": {"vssgp.devs"}}
    out = pv.build_effective_map(aces, gou, {}, ACTIONS_REL)
    assert 2 not in out["aad.u1"]
    assert 1 in out["aad.u1"] and 4 in out["aad.u1"]


def test_effective_usuario_sin_permisos():
    aces = {"vssgp.otros": {"allow": 2, "deny": 0}}
    gou = {"aad.u1": {"vssgp.devs"}}  # su grupo NO está en las ACEs
    out = pv.build_effective_map(aces, gou, {}, ACTIONS_REL)
    assert "aad.u1" not in out


def test_sensitive_names():
    bit_map = {1: "directa", 2: "grupo:X", 128: "grupo:X"}
    assert pv.sensitive_names(bit_map, ACTIONS_REL) == [
        "EditReleaseDefinition", "ManageReleases"]


# ═════════════════════════════════════════════════════════════════════════════
# Identidades / búsqueda
# ═════════════════════════════════════════════════════════════════════════════
def test_find_user_por_email():
    users = [_user(mail="ana@x.com"), _user("aad.u2", "Bob", "b@x.com")]
    assert pv.find_user(users, "ANA@X.COM").name == "Ana"


def test_find_user_por_nombre_parcial():
    users = [_user("aad.u1", "Ana Maria", "a@x.com"),
             _user("aad.u2", "Bob", "b@x.com")]
    assert pv.find_user(users, "maria").name == "Ana Maria"
    assert pv.find_user(users, "zzz") is None


def test_load_expected_users_lista():
    assert pv.load_expected_users("a@x.com, B@x.COM , ,c@x.com") == {
        "a@x.com", "b@x.com", "c@x.com"}


def test_load_expected_users_archivo(tmp_path):
    f = tmp_path / "expected.txt"
    f.write_text("a@x.com\n# comentario\n b@x.com \n\n", encoding="utf-8")
    assert pv.load_expected_users(str(f)) == {"a@x.com", "b@x.com"}


# ═════════════════════════════════════════════════════════════════════════════
# Tokens → nombre de recurso
# ═════════════════════════════════════════════════════════════════════════════
def test_token_resource_name_cd():
    names = {"cd": {1403: "oms-CD"}, "ci": {}, "repo": {}}
    nm, rid = pv.token_resource_name("release", "proj-1/1403", names)
    assert nm == "oms-CD" and rid == "1403"


def test_token_resource_name_raiz():
    nm, rid = pv.token_resource_name("release", "proj-1", {})
    assert "nivel CD" in nm and rid == ""


def test_token_resource_name_repo():
    names = {"repo": {"r1": "orders-repo"}}
    nm, rid = pv.token_resource_name("git", "repoV2/p1/r1", names)
    assert nm == "orders-repo"


# ═════════════════════════════════════════════════════════════════════════════
# Export rows / helpers puros de salida
# ═════════════════════════════════════════════════════════════════════════════
def test_export_rows():
    ur = {"name": "Ana", "mail": "a@x", "groups_str": "G1",
          "cd": "2 res", "ci": "—", "repo": "—", "proj": "—",
          "sens": "Edit", "expected": "no"}
    assert pv.export_row_user(ur)["esperado"] == "no"
    rr = {"resource": "cd-1", "kind": "CD", "n_users": 3,
          "sens": "Edit", "via": "grupo:X", "alert": "⚠ a"}
    assert pv.export_row_resource(rr)["usuarios_con_acceso"] == 3


def test_vssps_vsrm():
    assert pv.vssps("https://dev.azure.com/o") == \
        "https://vssps.dev.azure.com/o"
    assert pv.vsrm("https://dev.azure.com/o") == \
        "https://vsrm.dev.azure.com/o"


def test_namespaces_config():
    for k, cfg in pv.NAMESPACES.items():
        assert "{pid}" in cfg["root_token"]
        assert cfg["ns_name"] and cfg["ns_id_fallback"]
