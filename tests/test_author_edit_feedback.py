import json

import pytest
from conftest import build_package, build_to_manuscript
from typer.testing import CliRunner

from content_harness import styles
from content_harness.cli import app
from content_harness.state import Run
from content_harness.storage import HarnessError, atomic_write, read_yaml


def test_package_feedback_freezes_user_text_without_registering(workspace):
    project, run = workspace
    build_package(run, project)
    registered = run.state.artifacts['publish-package'].registered_hash
    article = run.artifact_path('publish-package') / 'article.md'
    edited = article.read_bytes() + '\n先试一次也可以。\n'.encode()
    atomic_write(article, edited)
    result = CliRunner().invoke(app, [
        '--project', str(project), 'style-feedback', run.state.run_id,
        '--artifact', 'publish-package', '--reason', '作者手改',
    ])
    assert result.exit_code == 0, result.output
    lesson = json.loads(result.output)['lesson']
    refreshed = Run(run.path)
    assert lesson['compared_member'] == 'article.md'
    assert lesson['before_hash'] == registered
    assert '先试一次' in lesson['diff']
    assert article.read_bytes() == edited
    snapshot = run.path / 'snapshots' / lesson['after_hash'].split(':')[1] / 'article.md'
    assert snapshot.read_bytes() == edited
    assert refreshed.state.artifacts['publish-package'].registered_hash == registered
    assert refreshed.state.artifacts['publish-package'].status != 'done'
    assert not refreshed.approved('publish')
    assert read_yaml(project / '.content-harness/style-memory/author.yaml')['rules'] == []


def test_historical_baseline_survives_intermediate_registration(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    first = run.hash('manuscript')
    path = run.artifact_path('manuscript')
    original = path.read_bytes()
    atomic_write(path, original + b'\nIntermediate edit\n')
    run.scan()
    run.register('manuscript')
    atomic_write(path, original + b'\nAuthor final edit\n')
    run.scan()
    lesson = styles.feedback(run, project, 'manuscript', 'run', 'compare first', first)
    assert 'Intermediate edit' not in lesson['diff']
    assert '+Author final edit' in lesson['diff']
    assert lesson['before_hash'] == first
    assert lesson['compared_member'] == 'content'


@pytest.mark.parametrize('bad_hash', ['../../escape', 'sha256:xx'])
def test_feedback_rejects_invalid_hash(workspace, bad_hash):
    project, run = workspace
    build_to_manuscript(run, project)
    with pytest.raises(HarnessError) as exc:
        styles.feedback(run, project, 'manuscript', 'run', 'bad', bad_hash)
    assert exc.value.code == 'INVALID_HASH'


def test_feedback_rejects_other_artifact_baseline(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    with pytest.raises(HarnessError) as exc:
        styles.feedback(run, project, 'manuscript', 'run', 'bad', run.hash('outline'))
    assert exc.value.code == 'BASELINE_NOT_REGISTERED'


def test_feedback_checks_snapshot_integrity(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    baseline = run.hash('manuscript')
    path = run.path / 'snapshots' / baseline.split(':')[1] / 'content'
    atomic_write(path, b'corrupt snapshot')
    with pytest.raises(HarnessError) as exc:
        styles.feedback(run, project, 'manuscript', 'run', 'bad')
    assert exc.value.code == 'SNAPSHOT_CORRUPT'


def test_metadata_edit_is_not_article_style_feedback(workspace):
    project, run = workspace
    build_package(run, project)
    atomic_write(run.artifact_path('publish-package') / 'titles.txt', b'New title\n')
    run.scan()
    with pytest.raises(HarnessError) as exc:
        styles.feedback(run, project, 'publish-package', 'run', 'metadata only')
    assert exc.value.code == 'NO_STYLE_DIFF'


def test_dimension_guidance_and_pack_changes_invalidate_contract(workspace, monkeypatch):
    project, run = workspace
    build_to_manuscript(run, project, ['natural-human-zh'])
    contract = read_yaml(run.artifact_path('voice-contract'))
    assert '边界适量' in contract['required_dimensions']
    assert '鼓励' in contract['dimension_guidance']['边界适量']
    original_pack = styles.pack

    def changed_pack(style_id):
        value = original_pack(style_id)
        if style_id == 'natural-human-zh':
            value['dimension_guidance']['边界适量'] += ' 新判据。'
        return value

    monkeypatch.setattr(styles, 'pack', changed_pack)
    assert styles.scan_voice_contract(run, project)
    assert run.state.artifacts['voice-contract'].status == 'stale'
    assert run.state.artifacts['manuscript'].status == 'stale'
