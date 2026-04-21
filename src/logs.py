import logging

_log_format = (
    "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
)

def set_logs() -> None:
    logging.basicConfig(
        format=_log_format,
        level=logging.INFO,
        filename="musservice.log",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_log_format))
    logging.getLogger("").addHandler(console)
