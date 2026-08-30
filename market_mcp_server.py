from mcp_servers.market_mcp_server import mcp, get_price, get_ohlc, get_news
from mcp_servers._common import run_server

if __name__ == "__main__":
    run_server(mcp, default_port=9002)
