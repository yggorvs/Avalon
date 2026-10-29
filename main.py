"""Compatibility terminal entrypoint."""
import sys
from avalon.__main__ import main
if __name__ == "__main__":
    sys.argv.append("--cli")
    main()
