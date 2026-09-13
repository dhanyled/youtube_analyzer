import argparse
import asyncio
import json

from youtube_analyzer.server.mcp_server import mcp, research_topic


def main():
    parser = argparse.ArgumentParser(description="Search Intelligence & YouTube Analyzer CLI")
    parser.add_argument(
        "topic", nargs="?", default="Google Ads untuk UMKM", help="Seed topic to research"
    )
    parser.add_argument("--serve", action="store_true", help="Start the FastMCP server")
    args = parser.parse_args()

    if args.serve:
        print("Starting YouTube Analyzer MCP Server...")
        mcp.run()
        return

    seed = args.topic
    print("=" * 60)
    print(f"Researching Topic: {seed}")
    print("=" * 60)

    result_json = asyncio.run(research_topic(seed))
    result = json.loads(result_json)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
