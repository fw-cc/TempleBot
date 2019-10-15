import pytz
import logging
import asyncio
from datetime import datetime
import json
import run


class Deadline:
    def __init__(self, deadline_dict):
        self.logger = logging.getLogger("GCHQBot.Deadline")
        self.deadline_dict = deadline_dict

    async def time_check(self):
        """Background deadline/task checking loop that is meant to sit on the main event loop"""
        global british_timezone
        while True:
            try:
                british_timezone = pytz.timezone('Europe/London')
                executed_deadlines = []
                for deadline, task_meta_struct in self.deadline_dict.items():
                    if deadline < datetime.now().isoformat():
                        execution_string = ""
                        for env_import in task_meta_struct[2]:
                            execution_string += f"; import {env_import}"
                        if task_meta_struct[1]:
                            execution_string += f"; asyncio.create_task({task_meta_struct[0]})"
                        elif not task_meta_struct[1]:
                            execution_string += f"{task_meta_struct[0]}"
                        exec(execution_string)
                        self.logger.info(f"Finished running task: {task_meta_struct[0]}, "
                                         f"removed from deadline list")
                        with open("./deadlines/deadline.json", "r+") as deadlines_json:
                            deadlines_struct = json.load(deadlines_json)
                        try:
                            del deadlines_struct[deadline]
                            with open("./deadlines/deadline.json", "w") as deadlines_json:
                                json.dump(deadlines_struct, deadlines_json, indent=4)
                        except KeyError:
                            pass
                        executed_deadlines.append(deadline)

                for deadline in executed_deadlines:
                    del self.deadline_dict[deadline]
            except Exception as e:
                self.logger.exception(e)
            await asyncio.sleep(30)

    async def add_deadline(self, datetime_obj, task: str, *imports, coro=False, use_file=True):
        """datetime_obj must be a timezone aware datetime object so it may be internally converted
        to UTC. task must be module aware i.e. function bar() in path foo/bar/foo.py must be
        properly instantiated, such that:
        deadlines.Deadline.add_deadline(datetime_obj, foo.bar(), "import foo.bar.foo") would
        be required to run the function correctly, note both the use of foo.bar() and the
        following import statement."""
        try:
            self.deadline_dict[datetime_obj.isoformat()] = [task, coro, list(imports)]
            self.logger.info(f"Added {datetime_obj} deadline with action {task} to execution list.")
        except AttributeError:
            self.deadline_dict[datetime_obj] = [task, coro, list(imports)]
            self.logger.info(f"Added {datetime_obj} deadline with action {task} to execution list.")

        if use_file:
            with open("./deadlines/deadline.json", "w", encoding="utf-8") as deadline_json:
                json.dump(self.deadline_dict, deadline_json, indent=2)
