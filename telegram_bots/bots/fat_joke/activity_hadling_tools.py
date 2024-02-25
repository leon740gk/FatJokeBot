from datetime import datetime


class ActivityHandler:

    def __init__(self, logger):
        self.date_format = "%Y-%m-%d %H:%M:%S"
        self.logger = logger

    def _get_last_activity_data(self, user_id, db):
        activity_date_select_query = f"""
        SELECT last_message_date FROM Users WHERE telegram_id = {user_id}
        """
        result = db.select_query(activity_date_select_query)[0][0]

        return result

    def _calculate_time_delta(self, last_activity_date):
        time_delta_days = 0
        if last_activity_date:
            now = datetime.now()
            last_activity_date = datetime.strptime(last_activity_date, self.date_format)
            time_delta_days = (now - last_activity_date).days

        return time_delta_days

    def _save_last_activity_data(self, user_id, db, last_activity_delta):
        now = datetime.now().strftime(self.date_format)
        activity_update_query = f"""
        UPDATE Users SET 
        activity_delta = {last_activity_delta},
        last_message_date = '{now}'
        WHERE telegram_id = {user_id}
        """
        db.commit_query(activity_update_query)

    def update_user_activity_data(self, user_id, db):
        last_activity_date = self._get_last_activity_data(user_id, db)
        activity_delta_days = self._calculate_time_delta(last_activity_date)
        self._save_last_activity_data(user_id, db, activity_delta_days)

    def check_daily_activity(self, db):
        select_all_user_ids_query = """
        SELECT telegram_id FROM Users
        """
        result_raw = db.select_query(select_all_user_ids_query)
        result = [i[0] for i in result_raw]

        for user_id in result:
            self.update_user_activity_data(user_id, db)
