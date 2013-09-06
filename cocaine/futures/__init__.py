from cocaine.exceptions import ChokeEvent


CLOSED_STATE_MESSAGE = 'invalid future object state - triggered while in closed state. Fix your code'


class Future(object):
    """A Future encapsulates the result of an asynchronous operation.

    In synchronous applications Futures are used to wait for the result from a thread or process pool. In cocaine
    they are normally used by yielding them in a chain.source context.

    :ivar state: current future's state. Can be one of the: `UNINITIALIZED`, `BOUND`, `CLOSED`.
    """
    UNITIALIZED, BOUND, CLOSED = range(3)

    def __init__(self):
        self._callback = None
        self._chunks = []

        self._errorback = None
        self._errors = []

        self.state = self.UNITIALIZED

    def bind(self, callback, errorback=None):
        """Binds callback and errorback to the future. Future immediately goes into `BOUND` state.

        When bound, future will trigger its callback and errorback on any pending value or error respectively.
        If there is no any callback attached to the future, it will store them into cache which will be emptied as
        `bind` method invoked.

        :param callback: callback which will be invoked on every pending result.
        :param errorback: errorback which will be invoked on every pending error.

        .. warning:: it's prohibited by design to call this method while future is already bounded.
        """
        assert self.state in (self.UNITIALIZED, self.CLOSED), 'double bind is prohibited by design'
        if errorback is None:
            errorback = self._default_errorback

        while self._chunks:
            callback(self._chunks.pop(0))
        while self._errors:
            errorback(self._errors.pop(0))

        if self.state == self.UNITIALIZED:
            self._callback = callback
            self._errorback = errorback
            self.state = self.BOUND

    def unbind(self):
        """Unbind future and transfer it to the `UNINITIALIZED` state.

        This method drops any previously attached callback or errorback. Therefore, future can be used even after
        calling this method - it just need to be rebounded.
        """
        self._callback = None
        self._errorback = None
        self.state = self.UNITIALIZED

    def close(self, silent=False):
        """Close future and transfer it to the `CLOSED` state.

        .. note:: it is safe to call this method multiple times.
        .. warning:: after closing Future is considered to be dead. Therefore, it can be rebound again.
        """
        if self.state == self.CLOSED:
            return

        if not silent:
            if self._errorback is None:
                self._errors.append(ChokeEvent())
            else:
                self._errorback(ChokeEvent())
        self._callback = None
        self._errorback = None
        self.state = self.CLOSED

    def trigger(self, chunk):
        """Trigger future and transfer chunk to the attached callback.

        If there is no callback attached, it will be stored until someone provides it by invoking `bind` method.

        :param chunk: value needed to be transferred.
        """
        assert self.state in (self.UNITIALIZED, self.BOUND), CLOSED_STATE_MESSAGE
        if self._callback is None:
            self._chunks.append(chunk)
        else:
            self._callback(chunk)

    def error(self, err):
        """Trigger future and transfer chunk to the attached errorback.

        If there is no errorback attached, it will be stored until someone provides it by invoking `bind` method.

        :param err: error needed to be transferred.
        """
        assert self.state in (self.UNITIALIZED, self.BOUND), CLOSED_STATE_MESSAGE
        if self._errorback is None:
            self._errors.append(err)
        else:
            self._errorback(err)

    def _default_errorback(self, err):
        print('Can\'t throw error without errorback %s' % str(err))


class Sleep(object):
    """ Allow to attach callback, which will be executed after giving period (in fact, not early).
    """

    def __init__(self, timeout):
        self._timeout = timeout

    def bind(self, callback, errorback=None, on_done=None):
        raise NotImplementedError('broken')


class NextTick(object):
    """ Allow to attach callback, which will be executed on the next iteration of reactor loop.

    It's useful for hard operations, using that from handle to avoid event loop blocking.
    """

    def __init__(self):
        pass

    def bind(self, callback, errorback=None, on_done=None):
        raise NotImplementedError('broken')
