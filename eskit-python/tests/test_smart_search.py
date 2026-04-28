from eskit.es import build_smart_query, token_to_exts


def test_token_to_exts():
    assert token_to_exts('.jpg') == ['jpg']
    assert token_to_exts('*.pdf') == ['pdf']
    assert token_to_exts('.jpg,.png') == ['jpg', 'png']
    assert token_to_exts('ODL') == []


def test_build_smart_query():
    query, exts = build_smart_query(['.jpg', 'ODL'])
    assert query == 'ODL'
    assert exts == ['jpg']

    query, exts = build_smart_query(['.pdf', 'ODL', 'report'])
    assert query == 'ODL report'
    assert exts == ['pdf']
