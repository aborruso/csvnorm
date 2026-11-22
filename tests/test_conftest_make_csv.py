"""Minimal check of the make_csv fixture."""


def test_make_csv_rows_and_insert(make_csv):
    path = make_csv(3, insert={2: b"caf\xe9"}, crlf=True)
    assert path.read_bytes() == (
        b"a,b,c,d,e\r\n1,1,1,1,1\r\n2,2,2,2,caf\xe9\r\n3,3,3,3,3\r\n"
    )


def test_make_csv_body(make_csv):
    assert make_csv(body=b"x\n").read_bytes() == b"x\n"
