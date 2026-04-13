"""
Tests unitarios para azdo_pr_master_checker.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.azdo.azdo_pr_master_checker import (
    is_wildcard_branch,
    filter_prs_by_branch_wildcard,
    normalize,
    find_cd_candidates_for_repo,
    find_cd_by_artifact_source,
    find_cd_for_repo_with_details,
    has_stage,
)


# ═══════════════════════════════════════════════════════════════════════════════
# is_wildcard_branch
# ═══════════════════════════════════════════════════════════════════════════════
class TestIsWildcardBranch:

    @pytest.mark.unit
    def test_exact_branch(self):
        assert is_wildcard_branch("master") is False

    @pytest.mark.unit
    def test_exact_branch_qa(self):
        assert is_wildcard_branch("QA") is False

    @pytest.mark.unit
    def test_star_wildcard(self):
        assert is_wildcard_branch("release/*") is True

    @pytest.mark.unit
    def test_star_prefix_wildcard(self):
        assert is_wildcard_branch("release/v*") is True

    @pytest.mark.unit
    def test_question_wildcard(self):
        assert is_wildcard_branch("release/v?.0") is True

    @pytest.mark.unit
    def test_multiple_stars(self):
        assert is_wildcard_branch("release/*/*") is True

    @pytest.mark.unit
    def test_empty_string(self):
        assert is_wildcard_branch("") is False


# ═══════════════════════════════════════════════════════════════════════════════
# filter_prs_by_branch_wildcard
# ═══════════════════════════════════════════════════════════════════════════════
class TestFilterPrsByBranchWildcard:

    @pytest.mark.unit
    def test_exact_branch_passthrough(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "master")
        assert len(result) == 2  # no filtering for exact branch

    @pytest.mark.unit
    def test_wildcard_release_star(self):
        prs = [
            {"targetRefName": "refs/heads/release/v1.0"},
            {"targetRefName": "refs/heads/release/v2.0"},
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "release/*")
        assert len(result) == 2
        assert all("release/" in pr["targetRefName"] for pr in result)

    @pytest.mark.unit
    def test_wildcard_release_v_star(self):
        prs = [
            {"targetRefName": "refs/heads/release/v1.0"},
            {"targetRefName": "refs/heads/release/v2.0"},
            {"targetRefName": "refs/heads/release/hotfix"},
            {"targetRefName": "refs/heads/master"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "release/v*")
        assert len(result) == 2
        assert all("release/v" in pr["targetRefName"] for pr in result)

    @pytest.mark.unit
    def test_wildcard_no_match(self):
        prs = [
            {"targetRefName": "refs/heads/master"},
            {"targetRefName": "refs/heads/QA"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "release/*")
        assert len(result) == 0

    @pytest.mark.unit
    def test_wildcard_empty_target_ref(self):
        prs = [
            {"targetRefName": ""},
            {"targetRefName": "refs/heads/release/v1.0"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "release/*")
        assert len(result) == 1

    @pytest.mark.unit
    def test_wildcard_missing_target_ref(self):
        prs = [
            {"otherField": "value"},
            {"targetRefName": "refs/heads/release/v1.0"},
        ]
        result = filter_prs_by_branch_wildcard(prs, "release/*")
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# normalize
# ═══════════════════════════════════════════════════════════════════════════════
class TestNormalize:

    @pytest.mark.unit
    def test_basic(self):
        assert normalize("My-Repo") == "myrepo"

    @pytest.mark.unit
    def test_underscores(self):
        assert normalize("my_repo_name") == "myreponame"

    @pytest.mark.unit
    def test_dots(self):
        assert normalize("my.repo") == "myrepo"

    @pytest.mark.unit
    def test_spaces(self):
        assert normalize("my repo") == "myrepo"

    @pytest.mark.unit
    def test_mixed(self):
        assert normalize("My-Repo_Name.v2") == "myreponamev2"


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_candidates_for_repo
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdCandidatesForRepo:

    @pytest.mark.unit
    def test_exact_match(self):
        release_defs = [
            {"id": 1, "name": "my-repo"},
            {"id": 2, "name": "other-repo"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) >= 1
        assert result[0][0] == 1  # cd_id
        assert result[0][1] == 100  # exact match score

    @pytest.mark.unit
    def test_prefix_match(self):
        release_defs = [
            {"id": 1, "name": "my-repo-cd"},
            {"id": 2, "name": "other-repo"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) >= 1
        assert result[0][0] == 1
        assert result[0][1] == 90  # prefix match score

    @pytest.mark.unit
    def test_no_match(self):
        release_defs = [
            {"id": 1, "name": "completely-different"},
        ]
        result = find_cd_candidates_for_repo("my-repo", release_defs)
        assert len(result) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_by_artifact_source
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdByArtifactSource:

    @pytest.mark.unit
    def test_match_found(self):
        cd_details = {
            1: {
                "name": "my-repo-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "my-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is not None
        assert result["name"] == "my-repo-cd"

    @pytest.mark.unit
    def test_case_insensitive(self):
        cd_details = {
            1: {
                "name": "My-Repo-CD",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "My-Repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is not None

    @pytest.mark.unit
    def test_no_match(self):
        cd_details = {
            1: {
                "name": "other-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "other-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is None

    @pytest.mark.unit
    def test_none_cd_detail_skipped(self):
        cd_details = {1: None, 2: {"name": "cd2", "artifacts": []}}
        result = find_cd_by_artifact_source("my-repo", cd_details)
        assert result is None

    @pytest.mark.unit
    def test_empty_details_map(self):
        result = find_cd_by_artifact_source("my-repo", {})
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# find_cd_for_repo_with_details
# ═══════════════════════════════════════════════════════════════════════════════
class TestFindCdForRepoWithDetails:

    @pytest.mark.unit
    def test_artifact_source_priority(self):
        release_defs = [{"id": 1, "name": "my-repo-cd"}]
        cd_details = {
            1: {
                "name": "my-repo-cd",
                "artifacts": [
                    {
                        "type": "Git",
                        "definitionReference": {
                            "definition": {"name": "my-repo"}
                        }
                    }
                ]
            }
        }
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None
        assert result["name"] == "my-repo-cd"

    @pytest.mark.unit
    def test_fallback_by_name(self):
        release_defs = [{"id": 1, "name": "my-repo"}]
        cd_details = {1: {"name": "my-repo", "artifacts": []}}
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None

    @pytest.mark.unit
    def test_none_detail_in_map(self):
        release_defs = [{"id": 1, "name": "my-repo"}]
        cd_details = {1: None}
        result = find_cd_for_repo_with_details("my-repo", release_defs, cd_details)
        assert result is not None  # falls back to release_def summary


# ═══════════════════════════════════════════════════════════════════════════════
# has_stage
# ═══════════════════════════════════════════════════════════════════════════════
class TestHasStage:

    @pytest.mark.unit
    def test_stage_found(self):
        detail = {"environments": [{"name": "validador"}, {"name": "produccion"}]}
        assert has_stage(detail, "validador") is True

    @pytest.mark.unit
    def test_stage_not_found(self):
        detail = {"environments": [{"name": "produccion"}]}
        assert has_stage(detail, "validador") is False

    @pytest.mark.unit
    def test_case_insensitive(self):
        detail = {"environments": [{"name": "Validador"}]}
        assert has_stage(detail, "validador") is True

    @pytest.mark.unit
    def test_no_environments(self):
        detail = {"environments": []}
        assert has_stage(detail, "validador") is False

    @pytest.mark.unit
    def test_missing_environments_key(self):
        detail = {}
        assert has_stage(detail, "validador") is False
