"""Entry point for household_mcp.server package execution."""

from ..mcp_server import args, mcp

if __name__ == "__main__":
    # transportはリスト型なので、最初の要素のみ渡す
    transport = args.transport[0]
    if transport == "stdio":
        mcp.run(transport=transport)
    else:
        mcp.run(transport=transport, host=args.host, port=args.port)
