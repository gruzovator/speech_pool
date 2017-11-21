import asyncio

__all__ = ['StreamBuffer']


class _Writer:
    def __init__(self, buf):
        self.buf = buf

    async def write(self, data_chunk):
        async with self.buf._cond:
            if self.buf._state != StreamBuffer._ST_RECEIVING:
                raise Exception('wrong buf state')
            self.buf._data.append(data_chunk)
            self.buf._cond.notify_all()

    async def close(self, inclomplete=False):
        """

        :param bool inclomplete: set flag when stream buffer data may be incomplete
        (e.g. there was an error while receiving data )
        :return:
        """
        async with self.buf._cond:
            if self.buf._state != StreamBuffer._ST_RECEIVING:
                raise Exception('wrong buf state')
            self.buf._state = StreamBuffer._ST_CLOSED_INCOMPLETE if inclomplete else StreamBuffer._ST_CLOSED
            self.buf._cond.notify_all()


class _Reader:
    def __init__(self, buf):
        self.buf = buf
        self.offset = 0

    async def read(self):
        async with self.buf._cond:
            while True:
                if self.offset < len(self.buf._data):
                    data_chunk = self.buf._data[self.offset]
                    self.offset += 1
                    return data_chunk
                if self.buf._state >= StreamBuffer._ST_CLOSED:
                    return None
                await self.buf._cond.wait()


class StreamBuffer:
    # states
    _ST_START = 0
    _ST_RECEIVING = 1  # write in progress
    _ST_CLOSED = 2
    _ST_CLOSED_INCOMPLETE = 3  # write process was interrupted

    def __init__(self):
        self._data = []  # list of data chunks
        self._state = self._ST_START
        self._cond = asyncio.Condition()

    def make_writer(self):
        if self._state is not self._ST_START:
            raise RuntimeError('can\'t create writer. Wrong staTE')
        self._state = self._ST_RECEIVING
        return _Writer(self)

    def make_reader(self):
        return _Reader(self)
