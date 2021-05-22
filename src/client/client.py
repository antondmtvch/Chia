import time
import asyncio

from src.controller import settings
from src.controller.logger import logger, Color

logger.name = 'commands-client'


async def commands_client(loop, config):
    try:
        reader, writer = await asyncio.open_connection(
            *config.LISTENER_ADDR, loop=loop
        )
    except ConnectionRefusedError as e:
        logger.error(Color.RED.format(e))
        return

    logger.info(Color.GREEN.format('Connected on %s:%s') % config.LISTENER_ADDR)
    time.sleep(1)

    while True:
        try:
            message = input(Color.YELLOW.format('Input [pause|resume]: '))
            writer.write(message.encode())
            data = await reader.read(1024)
            logger.info(Color.GREEN.format('Response: %s') % data.decode())
            time.sleep(0.5)
        except KeyboardInterrupt:
            command = input(Color.BLUE.format('Close client? [yes/no]: ')).lower()
            if command == 'yes':
                break
    writer.close()
    logger.info(Color.GREEN.format('Commands client: Close'))


def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        commands_client(loop, settings)
    )
    loop.close()
