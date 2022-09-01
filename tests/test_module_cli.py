import pytest
import json
from urllib.parse import urljoin
from unittest.mock import MagicMock, patch, mock_open

from picterra.__main__ import parse_args
from picterra.helpers import APIClient
from picterra import __main__
from picterra.command_parsers import detect, create


def _mock_read_in_chunks(f):
    return ['qui', 'noa']

def _fake__init__(s):
    s.base_url = 'www.example.com'
    s.api_key = 'foobar'

def test_parser_arg_errors(capsys):
    # SystemExit does not inherit from Exception
    with pytest.raises(BaseException):
        parse_args(['-foobar', '-spam'])
    captured = capsys.readouterr()
    assert 'unrecognized arguments' in captured.err
    assert 'foobar' in captured.err


def test_rasters_list(monkeypatch):
    # Setup
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_rasterlist = MagicMock(return_value=['foo', 'bar'])
    assert mock_rasterlist.called is False
    monkeypatch.setattr(APIClient, 'list_rasters', mock_rasterlist)
    parse_args(['list', 'rasters'])
    assert mock_rasterlist.called is True
    mock_rasterlist.reset_mock()
    assert mock_rasterlist.called is False
    parse_args(['list', 'rasters', '--folder', 'foobar', '--search', 'spam'])
    mock_rasterlist.assert_called_with('foobar', 'spam')

def test_rasters_list_output_format(monkeypatch, capsys):
    # Setup
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_rasterlist = MagicMock(return_value=[{'id': 4, 'name': 'foo'}, {'id': 5, 'name': 'bar'}])
    assert mock_rasterlist.called is False
    monkeypatch.setattr(APIClient, 'list_rasters', mock_rasterlist)
    # JSON
    for a in ['list', 'rasters'], ['list', 'rasters', '--output', 'json']:
        parse_args(a)
        assert json.loads(capsys.readouterr().out.replace("\n", "")) == json.loads('[{"id": 4, "name": "foo"}, {"id": 5, "name": "bar"}]')
        assert mock_rasterlist.called is True
        mock_rasterlist.reset_mock()
        assert mock_rasterlist.called is False
    # IDs only
    parse_args(['list', 'rasters', '--output', 'ids_only'])
    assert mock_rasterlist.called is True
    assert capsys.readouterr().out.replace("\n", "", 2) == '45'


def test_detectors_list(monkeypatch):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_detectorslist = MagicMock(return_value=['foo', 'bar'])
    mock_detectorslist.called is False
    monkeypatch.setattr(APIClient, 'list_detectors', mock_detectorslist)
    parse_args(['list', 'detectors'])
    mock_detectorslist.called is True

def test_prediction(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_run, mock_download_file, mock_download_url, mock_url = MagicMock(return_value='foobar'), MagicMock(),  MagicMock(), MagicMock(return_value='spam')
    monkeypatch.setattr(APIClient, 'run_detector', mock_run)
    monkeypatch.setattr(APIClient, 'download_result_to_feature_collection', mock_download_file)
    monkeypatch.setattr(APIClient, 'download_operation_results_to_file', mock_download_url)
    monkeypatch.setattr(APIClient, 'get_operation_results_url', mock_url)
    monkeypatch.setattr(detect, '_read_in_chunks', _mock_read_in_chunks)
    with pytest.raises(BaseException):
        parse_args(['detect'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert (mock_run.called or mock_download_file.called or mock_url.called) is False
    with pytest.raises(BaseException):
        parse_args(['detect', 'my_raster_id'])
    assert 'following arguments are required' in captured.err
    assert 'detector' in captured.err
    assert (mock_run.called or mock_download_file.called or mock_url.called) is False
    # Base (print URL)
    assert mock_download_url.called is False
    parse_args(['detect', 'my_raster_id', 'my_detector_id'])
    assert capsys.readouterr().out.replace('\n', '') == 'spam'
    assert capsys.readouterr().err == ''
    mock_run.reset_mock()
    mock_download_file.reset_mock()
    mock_url.reset_mock()
    parse_args(['detect', 'my_raster_id', 'my_detector_id', '--output-type', 'url'])
    assert capsys.readouterr().out.replace('\n', '') == 'spam'
    assert capsys.readouterr().err == ''
    mock_run.reset_mock()
    mock_download_file.reset_mock()
    mock_url.reset_mock()
    # Print result data
    assert mock_download_url.called is False
    parse_args(['detect', 'my_raster_id', 'my_detector_id', '--output-type', 'geometries'])
    assert capsys.readouterr().out == 'quinoa'
    assert capsys.readouterr().err == ''
    assert mock_run.called is True
    assert mock_download_file.called is True
    assert mock_download_url.called is False
    mock_run.reset_mock()
    mock_download_file.reset_mock()
    mock_url.reset_mock()
    # Write result URL to file
    assert mock_download_url.called is False
    mock_open = MagicMock()
    with patch('builtins.open', new_callable=mock_open()):
        parse_args(['detect', 'my_raster_id', 'my_detector_id', '--output-type', 'url', '--output-file', 'a_path'])
    assert capsys.readouterr().out +  capsys.readouterr().err == ''
    assert mock_download_url.called is True
    assert mock_download_file.called is False
    mock_download_url.assert_called_with('foobar', 'a_path')
    mock_download_url.reset_mock()
    with patch('builtins.open', new_callable=mock_open()):
        parse_args(['detect', 'my_raster_id', 'my_detector_id', '--output-file', 'a_path'])
    assert capsys.readouterr().out + capsys.readouterr().err == ''
    assert mock_download_url.called is True
    assert mock_download_file.called is False
    mock_download_url.assert_called_with('foobar', 'a_path')
    mock_download_url.reset_mock()
    # Write result data to file
    assert mock_download_file.called is False
    with patch('builtins.open', new_callable=mock_open()):
        parse_args(['detect', 'my_raster_id', 'my_detector_id', '--output-type', 'geometries', '--output-file', 'a_path'])
        assert capsys.readouterr().out + capsys.readouterr().err == ''
        assert mock_download_file.called is True
        mock_download_file.assert_called_with('foobar', 'a_path')


def test_train(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_train = MagicMock()
    monkeypatch.setattr(APIClient, 'train_detector', mock_train)
    with pytest.raises(BaseException):
        parse_args(['train'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'detector' in captured.err
    assert mock_train.called is False
    parse_args(['train', 'my_detector_id'])
    mock_train.assert_called_with('my_detector_id')


def test_create_detector(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_create_detector, mock_add_raster = MagicMock(return_value='spam'), MagicMock()
    monkeypatch.setattr(APIClient, 'create_detector', mock_create_detector)
    monkeypatch.setattr(APIClient, 'add_raster_to_detector', mock_add_raster)
    assert mock_create_detector.called is False
    assert mock_add_raster.called is False
    parse_args(['create', 'detector'])
    mock_create_detector.assert_called_with(None, 'count', 'polygon', 500)
    assert mock_add_raster.call_count == 0
    mock_create_detector.reset_mock()
    mock_add_raster.reset_mock()
    parse_args([
        'create', 'detector',
        '--output-type', 'bbox', '--detection-type', 'segmentation',
        '--raster', 'foo', '--training-steps', '888',
        '--name', 'foobar'])
    mock_create_detector.assert_called_with('foobar', 'segmentation', 'bbox', 888)
    assert mock_add_raster.call_count == 1
    mock_add_raster.assert_called_with('foo', 'spam')


def test_create_raster__from_file(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_create_raster, mock_add_raster = MagicMock(return_value='spam'), MagicMock()
    mock_raster_datetime_name = MagicMock(return_value='foobar')
    monkeypatch.setattr(APIClient, 'upload_raster', mock_create_raster)
    monkeypatch.setattr(APIClient, 'add_raster_to_detector', mock_add_raster)
    monkeypatch.setattr(create, '_raster_datetime_name', mock_raster_datetime_name)
    assert mock_create_raster.called is False
    assert mock_add_raster.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'raster', 'file'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'path' in captured.err
    with pytest.raises(BaseException):
        parse_args(['create', 'raster'])
    captured = capsys.readouterr()
    assert 'usage' in captured.out
    assert mock_create_raster.called is False
    assert mock_add_raster.called is False
    parse_args(['create', 'raster', 'file', 'my_path_to_tiff'])
    mock_create_raster.assert_called_with(
        'my_path_to_tiff', 'foobar', None, multispectral=False)
    assert mock_add_raster.called is False
    mock_create_raster.reset_mock()
    mock_add_raster.reset_mock()
    parse_args([
        'create', 'raster', 'file', 'my_path_to_tiff', '--name', 'beacon', '--folder', 'eggs',
        '--detector', 'a', 'b', 'c', '--multispectral'
    ])
    mock_create_raster.assert_called_with(
        'my_path_to_tiff', 'beacon', 'eggs', multispectral=True)
    assert mock_add_raster.call_count == 3
    mock_add_raster.assert_called_with('spam', 'c')


def test_create_raster__from_remote(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_create_raster, mock_add_raster = MagicMock(return_value='spam'), MagicMock()
    monkeypatch.setattr(APIClient, 'upload_remote_raster', mock_create_raster)
    monkeypatch.setattr(APIClient, 'add_raster_to_detector', mock_add_raster)
    assert (mock_create_raster.called or mock_add_raster.called) is False
    # Errors
    with pytest.raises(BaseException):
        parse_args(['create', 'raster'])
    captured = capsys.readouterr()
    assert 'usage' in captured.out
    with pytest.raises(BaseException):
        parse_args(['create', 'raster', 'remote'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'resolution' in captured.err
    assert (mock_create_raster.called or mock_add_raster.called) is False
    for bad_coords in ('5.0,50.0,6.0', '5.0,50.0,6.0,60.0,88.0'):
        with pytest.raises(BaseException):
            parse_args([
            'create', 'raster', 'remote',
            'xyz', 'https://xyz.example.org', '0.25', bad_coords
            ])
        assert '4 coordinates' in  capsys.readouterr().err
        assert (mock_create_raster.called or mock_add_raster.called) is False
    for bad_coords in ('5.0,50.0,6.0,99.0', '225.0,50.0,6.0,60.0'):
        with pytest.raises(BaseException):
            parse_args([
            'create', 'raster', 'remote',
            'xyz', 'https://xyz.example.org', '0.25', bad_coords
            ])
        assert 'valid' in  capsys.readouterr().err
        assert (mock_create_raster.called or mock_add_raster.called) is False
    for bad_coords in ('5.0,50.0,6.0,40.0', '8.0,50.0,6.0,60.0'):
        with pytest.raises(BaseException):
            parse_args([
            'create', 'raster', 'remote',
            'xyz', 'https://xyz.example.org', '0.25', bad_coords
            ])
        assert 'order' in  capsys.readouterr().err
        assert (mock_create_raster.called or mock_add_raster.called) is False
    # Working cases
    parse_args([
        'create', 'raster', 'remote',
        'xyz', 'https://xyz.example.org', '0.25', '5.0,50.0,6.0,60.0'])
    footprint = {
        "type": "Polygon",
        "coordinates": [[[5.0, 50.0], [6.0, 50.0], [6.0, 60.0], [5.0, 60.0], [5.0, 50.0]]]
    }
    mock_create_raster.assert_called_with(
        'xyz', 'https://xyz.example.org', 0.25, footprint, None, None, None)
    assert mock_add_raster.called is False
    mock_create_raster.reset_mock()
    mock_add_raster.reset_mock()
    parse_args([
        'create', 'raster', 'remote',
        'xyz', 'https://xyz.example.org', '0.25', '5.0,50.0,6.0,60.0',
        '--credentials', 'foo:bar',
        '--name', 'beacon', '--folder', 'eggs',
        '--detector', 'a', 'b', 'c'
    ])
    mock_create_raster.assert_called_with(
        'xyz', 'https://xyz.example.org', 0.25, footprint, 'foo:bar', 'beacon',  'eggs')
    assert mock_add_raster.call_count == 3
    mock_add_raster.assert_called_with('spam', 'c')


def test_create_annotation(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_set_annotations = MagicMock()
    monkeypatch.setattr(APIClient, 'set_annotations', mock_set_annotations)
    assert mock_set_annotations.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'annotation'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'type' in captured.err
    assert mock_set_annotations.called is False
    with patch("builtins.open", mock_open(read_data='{"a":3}')):
        parse_args([
            'create', 'annotation', 'path/to/open', 'my_raster', 'my_detector',
            'training_area'
        ])
        mock_set_annotations.assert_called_with(
            'my_detector', 'my_raster', 'training_area', {"a":3})


def test_create_detectionarea(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_set_detectionarea = MagicMock()
    monkeypatch.setattr(
        APIClient, 'set_raster_detection_areas_from_file', mock_set_detectionarea)
    assert mock_set_detectionarea.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'detection_area'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'path' in captured.err
    assert mock_set_detectionarea.called is False
    parse_args([
        'create', 'detection_area', 'path/to/open', 'my_raster'
    ])
    mock_set_detectionarea.assert_called_with('my_raster', 'path/to/open')


def test_delete_raster(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_delete = MagicMock()
    monkeypatch.setattr(APIClient, 'delete_raster', mock_delete)
    assert mock_delete.called is False
    with pytest.raises(BaseException):
        parse_args(['delete', 'raster'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert mock_delete.called is False
    parse_args(['delete', 'raster', 'my_raster'])
    mock_delete.assert_called_with('my_raster')


def test_edit_raster(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_edit = MagicMock()
    monkeypatch.setattr(APIClient, 'edit_raster', mock_edit)
    assert mock_edit.called is False
    with pytest.raises(BaseException):
        parse_args(['edit', 'raster'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert mock_edit.called is False
    parse_args(['edit', 'raster', 'a-raster-uuid', '--name', 'beacon'])
    mock_edit.assert_called_with('a-raster-uuid', name='beacon')


def test_delete_detector(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_delete = MagicMock()
    monkeypatch.setattr(APIClient, 'delete_detector', mock_delete)
    assert mock_delete.called is False
    with pytest.raises(BaseException):
        parse_args(['delete', 'detector'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'detector' in captured.err
    assert mock_delete.called is False
    parse_args(['delete', 'detector', 'my_detector'])
    mock_delete.assert_called_with('my_detector')


def test_delete_detectionarea(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_delete = MagicMock()
    monkeypatch.setattr(APIClient, 'remove_raster_detection_areas', mock_delete)
    assert mock_delete.called is False
    with pytest.raises(BaseException):
        parse_args(['delete', 'detection_area'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert mock_delete.called is False
    parse_args(['delete', 'detection_area', 'my_raster'])
    mock_delete.assert_called_with('my_raster')

def test_download_raster(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    mock_download = MagicMock()
    monkeypatch.setattr(APIClient, 'download_raster_to_file', mock_download)
    assert mock_download.called is False
    with pytest.raises(BaseException):
        parse_args(['download', 'raster', 'my_raster_id'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'path' in captured.err
    assert mock_download.called is False
    parse_args(['download', 'raster', 'my_raster_id', 'a_path'])
    assert mock_download.called is True
    mock_download.assert_called_with('my_raster_id', 'a_path')


@pytest.mark.parametrize("args,content", [
    ([], '{create,delete,detect,download,edit,list,train}'),
    (['list'], "List user's detectors"),
    (['create'], "Add an annotation to a raster for a given detector"),
    (['create raster'], "Uploads raster from a local file"),
    (['create annotation'], "following arguments are required: path, raster, detector"),
    (['create detection_area'], "required: path, raster"),
    (['delete'], "Removes the detection areas of raster, if any"),
    (['delete raster'], "{raster}"),
    (['detect'], "[--output-type {url,geometries}]"),
    (['download'], "Downloads a raster"),
    (['edit'], "usage: picterra edit [-h] {raster}"),
    (['create train'], "required: detector"),
])
def test_parser_specific_helpers(monkeypatch, capsys, args, content):
    """Checks different helpers are shown depending on subparser"""
    monkeypatch.setattr(APIClient, '__init__', _fake__init__)
    with pytest.raises(BaseException):
        parse_args(args)
        captured = capsys.readouterr()
        assert content in captured.err
