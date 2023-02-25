from kedixa.file_loader import file_loader, mfile_loader

def test_file_loader_01():
    filename = 'files/a.txt'
    total01, total02 = 0, 0

    for batch in file_loader(filename, 7):
        total01 += len(batch)

    with open(filename) as f:
        for _ in f:
            total02 += 1

    assert total01 == total02

def test_file_loader_02():
    filename = 'files/a.txt'
    total01, total02 = 0, 0

    with open(filename) as f:
        for batch in file_loader(f, 7):
            total01 += len(batch)

    with open(filename) as f:
        for _ in f:
            total02 += 1

    assert total01 == total02

def test_file_loader_03():
    import io
    cnt = 1000
    lines = '\n'.join([str(i) for i in range(cnt)])

    total = 0
    for batch in file_loader(io.StringIO(lines)):
        total += len(batch)

    assert total == cnt

def test_mfile_loader_01():
    filenames = ['files/a.txt', 'files/b.txt']
    total01, total02 = 0, 0

    for batch in mfile_loader(filenames, 19):
        total01 += len(batch)

    for fn in filenames:
        with open(fn) as f:
            for _ in f:
                total02 += 1

    assert total01 == total02
