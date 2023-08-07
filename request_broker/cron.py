from django_cron import CronJobBase, Schedule

from process_request.helpers import refresh_reading_room_cache
from request_broker.settings import AEON


class RefreshReadingRoomCache(CronJobBase):
    schedule = Schedule(run_every_mins=AEON["cache_duration"])
    code = 'request_broker.refresh_reading_room_cache'

    def do(self):
        refresh_reading_room_cache()
