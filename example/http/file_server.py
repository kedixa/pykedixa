import asyncio
import argparse
import signal
import os

from kedixa.comm.http import (
    HttpRequest,
    HttpResponse,
    HttpChunkTransformer,
)
from kedixa.comm import (
    Connection,
    ReadUntilTransformer,
    AdaptorEofError,
    TransformerEofError,
    TcpServer,
    FileAdaptor,
    TcpAdaptor,
    CommBridge,
)

class SimpleFileService:
    TextSuffix = [
        '.txt', '.c', '.cc', '.cpp', '.py', '.java', '.ipynb', '.md',
        '.yml', '.yaml', '.json', '.xml', '.rs', '.go', '.lua', '.sh',
    ]
    TextFiles = [
        '.gitignore', 'makefile', 'gnumakefile', 'dockerfile',
    ]
    ImageSuffix = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

    def __init__(self, root=None):
        if root is None:
            root = os.getcwd()

        root = os.path.abspath(root)
        assert os.path.isdir(root)
        self._root = root

    def get_path(self, uri: str):
        path = uri

        pos = path.find('?')
        if pos >= 0:
            path = path[:pos]

        pos = path.find('#')
        if pos >= 0:
            path = path[:pos]

        path = path.strip('/')
        parts = path.split('/')
        return os.path.join(self._root, *parts), path

    def is_text(self, filename: str) -> bool:
        basename, ext = os.path.splitext(filename)
        if not ext:
            return basename.lower() in self.TextFiles
        return ext.lower() in self.TextSuffix

    def is_image(self, filename: str) -> bool:
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.ImageSuffix

    async def process_dir(self, conn: Connection, path: str, relative: str):
        pos = relative.rfind('/')
        parent = '' if pos <= 0 else relative[:pos]

        resp = HttpResponse()
        resp.set_header('Connection', 'Keep-Alive')
        try:
            head = '<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /></head>'
            body = f'<html>{head}\n<body>\n'
            body += f'<p>当前目录: /{relative}</a></p>\n'
            body += f'<p><a href="/">⏎ 返回根目录</a></p>\n'
            if parent:
                body += f'<p><a href="/{parent}">← 返回父目录</a></p>\n'

            body += '<ul>'
            for fn in os.listdir(path):
                p = os.path.join(path, fn)
                fn_url = os.path.join('/', relative, fn)

                if os.path.isdir(p):
                    body += f'<li>📁 <a href="{fn_url}">{fn}</a></li>\n'
                elif self.is_text(fn):
                    body += f'<li>📄 <a href="{fn_url}" target="_blank">{fn}</a></li>\n'
                elif self.is_image(fn):
                    body += f'<li>🏞 <a href="{fn_url}" target="blank">{fn}</a></li>\n'
                else:
                    body += f'<li>💾 <a href="{fn_url}" download="{fn}">{fn}</a></li>\n'

            body += '</ul>\n</body></html>\n'
            resp.set_body(body.encode())
        except:
            resp.set_http_status(500, 'Internal Server Error')
            resp.set_body(b'<html><body>500 Internal Server Error</body></html>')
        await conn.request(resp, None)

    async def process_file(self, conn: Connection, path: str):
        resp = HttpResponse()
        resp.set_header('Connection', 'keep-alive')
        resp.set_header('Transfer-Encoding', 'chunked')
        resp.set_empty_body(True)

        await resp.encode(conn.c)

        # send file with http chunk
        fa = FileAdaptor(path)
        chunk = HttpChunkTransformer()
        chunk.bind_next(conn.c)

        async with fa, chunk:
            bridge = CommBridge(fa, chunk)
            await bridge.run()
            await chunk.flush()

    async def process(self, conn: Connection):
        await conn.bind(ReadUntilTransformer())
        adaptor : TcpAdaptor = conn.adaptor
        addr = adaptor.addr
        peer = f'{addr.ip}:{addr.port}'

        while not conn.closed():
            req = HttpRequest()
            try:
                await conn.request(None, req)
            except (AdaptorEofError, TransformerEofError):
                break

            url = req.get_req_url()
            print(f'Request from:{peer} url:{url}')

            local, relative = self.get_path(url)
            if os.path.isdir(local):
                await self.process_dir(conn, local, relative)
            elif os.path.isfile(local):
                await self.process_file(conn, local)
            else:
                resp = HttpResponse()
                resp.set_http_status(404, 'Not Found')
                resp.set_header('Connection', 'Keep-Alive')
                body = '<html><body>404 Not Found</body></html>'
                resp.set_body(body.encode())
                await conn.request(resp, None)

def get_processor(service: SimpleFileService):
    async def wrapper(conn: Connection):
        await service.process(conn)
    return wrapper

async def run(port: int, fs_root: str):
    if fs_root is None:
        fs_root = os.getcwd()
    fs_root = os.path.abspath(fs_root)
    assert os.path.isdir(fs_root)

    print(f'start http file server at {fs_root} on port {port}')
    service = SimpleFileService(fs_root)
    server = TcpServer(listen_port=port, processor=get_processor(service))
    await server.start()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: server.stop())
    loop.add_signal_handler(signal.SIGTERM, lambda: server.stop())

    try:
        await server.run_forever()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        print(f'wait finish')
        await server.wait_finish()
        print(f'stop done')

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000, help='')
    parser.add_argument('-r', '--root', type=str, default=None, help='')
    args = parser.parse_args()
    await run(args.port, args.root)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
