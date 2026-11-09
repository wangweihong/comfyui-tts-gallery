"""Isolated HTTP preview; never writes the real ComfyUI user library."""
import argparse
from pathlib import Path
from aiohttp import web
from support import catalog, routes, ROOT

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8194); args=parser.parse_args()
    library=catalog.Library(user=ROOT/'.generation'/'preview-user')
    table=web.RouteTableDef(); routes.register_routes(table,library)
    app=web.Application(client_max_size=30*1024*1024);app.add_routes(table)
    web.run_app(app,host='0.0.0.0',port=args.port)
