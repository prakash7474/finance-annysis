from mcp_servers.bank_mcp_server import mcp, get_accounts, get_transactions, get_loan_offers
from mcp_servers._common import run_server

if __name__ == "__main__":
    run_server(mcp, default_port=9001)
