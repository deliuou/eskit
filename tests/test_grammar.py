from eskit.grammar import parse_search_tokens


def test_direct_pdf_search():
    spec = parse_search_tokens(['.pdf', 'ODL'])
    assert spec.roots == []
    assert spec.exts == ['pdf']
    assert spec.name_tokens == ['ODL']
    assert spec.query == 'ODL'


def test_drive_type_name():
    spec = parse_search_tokens(['d', '.pdf', 'ODL'])
    assert spec.roots == ['D:\\']
    assert spec.exts == ['pdf']
    assert spec.name_tokens == ['ODL']


def test_multiple_drives_and_types():
    spec = parse_search_tokens(['d', 'e', '.jpg', '.png', 'ODL'])
    assert spec.roots == ['D:\\', 'E:\\']
    assert spec.exts == ['jpg', 'png']
    assert spec.name_tokens == ['ODL']


def test_path_alias_root():
    spec = parse_search_tokens(['d/Projects', '.pdf', '开题'])
    assert spec.roots == ['D:\\Projects']
    assert spec.exts == ['pdf']
    assert spec.name_tokens == ['开题']


def test_single_letter_after_query_is_filename_token():
    spec = parse_search_tokens(['.pdf', 'ODL', 'd'])
    assert spec.roots == []
    assert spec.exts == ['pdf']
    assert spec.name_tokens == ['ODL', 'd']


def test_multiple_bare_drives_without_type():
    spec = parse_search_tokens(['d', 'f', 'ODL'])
    assert spec.roots == ['D:\\', 'F:\\']
    assert spec.exts == []
    assert spec.name_tokens == ['ODL']


def test_folder_kind_token():
    spec = parse_search_tokens(['d', 'folder', 'ODL'])
    assert spec.roots == ['D:\\']
    assert spec.exts == []
    assert spec.kinds == ['folder']
    assert spec.name_tokens == ['ODL']


def test_chinese_folder_kind_token():
    spec = parse_search_tokens(['d', '文件夹', '开题'])
    assert spec.roots == ['D:\\']
    assert spec.kinds == ['folder']
    assert spec.name_tokens == ['开题']


def test_folder_and_ext_mixed_search():
    spec = parse_search_tokens(['d', 'folder', '.pdf', 'ODL'])
    assert spec.roots == ['D:\\']
    assert spec.exts == ['pdf']
    assert spec.kinds == ['folder', 'file']
    assert spec.name_tokens == ['ODL']


def test_file_kind_token():
    spec = parse_search_tokens(['d', 'file', 'ODL'])
    assert spec.roots == ['D:\\']
    assert spec.kinds == ['file']
    assert spec.name_tokens == ['ODL']
