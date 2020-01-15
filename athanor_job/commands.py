import math, datetime
from django.conf import settings
import evennia
from evennia.utils.utils import time_format, class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

JOB_COLUMNS = f"*    ID Submitter       Title                         Claimed         Due  Lst"


class JobCmd(COMMAND_DEFAULT_CLASS):
    account_caller = True
    system_name = "JOBS"
    help_category = "Job System / Issue Tracker"

    def display_job(self, lhs):
        admin = False
        job = evennia.GLOBAL_SCRIPTS.jobs.find_job(self.account, self.lhs)
        if job.bucket.access(self.account, 'admin') or job.links.filter(link_type=2, account_stub=self.account.stub):
            admin = True
        message = list()
        message.append(self.styled_header(f'{job.bucket} Job {job.id} - {job.status_word()}'))
        message.append(f"|hTitle:|n {job.title}")
        message.append(f'|hHandlers:|n {job.handler_names()}')
        message.append(f'|hHelpers:|n {job.helper_names()}')
        comments = job.comments()
        if not admin:
            comments = comments.exclude(is_private=True)
        for com in comments:
            message.append(self.styled_separator())
            message.append(com.display(self.account, admin))
        message.append(self.styled_footer(f"Due: {self.account.display_time(job.due_date)}"))
        job.update_read(self.account)
        self.msg('\n'.join(message))

    def display_buckets(self):
        message = list()
        message.append(self.styled_header('Job Buckets'))
        col_color = self.account.options.column_names_color
        message.append(f"|{col_color}Name     Description                        Pen  App  Dny  Cnc  Over Due  Anon|n")
        message.append(self.styled_separator())
        for bucket in evennia.GLOBAL_SCRIPTS.jobs.visible_buckets(self.account):
            bkey = bucket.key[:8].ljust(8)
            description = bucket.description
            if not description:
                description = ""
            pending = str(bucket.jobs.filter(status=0).count()).rjust(3).ljust(4)
            approved = str(bucket.jobs.filter(status=1).count()).rjust(3).ljust(4)
            denied = str(bucket.jobs.filter(status=2).count()).rjust(3).ljust(4)
            canceled = str(bucket.jobs.filter(status=3).count()).rjust(3).ljust(4)
            anon = 'No'
            now = datetime.datetime.utcnow()
            overdue = str(bucket.jobs.filter(status=0, due_date__lt=now).count()).rjust(3).ljust(4)
            due = time_format(bucket.due.total_seconds(), style=1).rjust(3)
            message.append(f"{bkey} {description[:34].ljust(34)} {pending} {approved} {denied} {canceled} {overdue} {due}  {anon}")
        message.append(self.styled_footer())
        self.msg('\n'.join(str(l) for l in message))

    def display_bucket(self, bucket, old=False):
        page = 1
        if '/' in bucket:
            bucket, page = bucket.split('/', 1)
            if page.isdigit():
                page = int(page)
            else:
                page = 1
        bucket = evennia.GLOBAL_SCRIPTS.jobs.find_bucket(self.account, bucket)
        admin = bucket.access(self.account, "admin")
        if not admin:
            raise ValueError("Permission denied.")
        if old:
            jobs = bucket.old()
        else:
            jobs = bucket.active()
        jobs_count = len(jobs)
        if not jobs_count:
            raise ValueError("No jobs to display!")
        pages = float(jobs_count) / 30.0
        pages = int(math.ceil(pages))
        if page > pages:
            page = pages
        if page < 1:
            page = 1
        message = list()
        message.append(self.styled_header(f"{'Old' if old else 'Active'} Jobs - {bucket}"))
        message.append(JOB_COLUMNS)
        message.append(self.styled_separator())
        for job in jobs:
            message.append(job.display_line(self.account, admin))
        message.append(self.styled_footer(f'< Page {page} of {pages} >'))
        self.msg("\n".join(str(l) for l in message))

    def switch_main(self):
        if self.args:
            if self.lhs.isdigit():
                self.display_job(self.lhs)
            else:
                self.display_bucket(self.lhs)
        else:
            self.display_buckets()


class CmdJBucket(JobCmd):
    key = '+jbucket'
    aliases = ['+jbuckets', ]
    locks = 'cmd:perm(Admin) or perm(Job_Admin)'
    switch_options = ['create', 'delete', 'rename', 'lock', 'due', 'describe']

    def switch_create(self):
        evennia.GLOBAL_SCRIPTS.jobs.create_bucket(self.account, self.lhs, self.rhs)

    def switch_delete(self):
        evennia.GLOBAL_SCRIPTS.jobs.delete_bucket(self.account, self.args)
        
    def switch_rename(self):
        evennia.GLOBAL_SCRIPTS.jobs.rename_bucket(self.account, self.lhs, self.rhs)

    def switch_lock(self):
        evennia.GLOBAL_SCRIPTS.jobs.lock_bucket(self.account, self.lhs, self.rhs)

    def switch_due(self):
        evennia.GLOBAL_SCRIPTS.jobs.due_bucket(self.account, self.lhs, self.rhs)

    def switch_describe(self):
        evennia.GLOBAL_SCRIPTS.jobs.describe_bucket(self.account, self.lhs, self.rhs)

    def switch_main(self):
        self.display_buckets()


class CmdJobAdmin(JobCmd):
    key = "+jadmin"
    switch_options = ['addhandler', 'remhandler', 'addhelper', 'remhelper', 'move', 'due', 'approve', 'deny', 'cancel',
                      'revive', 'claim', 'unclaim']

    def switch_claim(self):
        self.switch_addhandler()

    def switch_unclaim(self):
        self.switch_remhandler()

    def switch_addhandler(self):
        if self.rhs:
            handler = self.account.search(self.rhs)
        else:
            handler = self.account
        evennia.GLOBAL_SCRIPTS.jobs.promote_account(self.account, self.lhs, handler, show_word="Handler",
                                                    rank=2, start_type=0)

    def switch_remhandler(self):
        if self.rhs:
            handler = self.account.search(self.rhs)
        else:
            handler = self.account
        evennia.GLOBAL_SCRIPTS.jobs.demote_account(self.account, self.lhs, handler, show_word="Handler",
                                                   rank=0, start_type=2)

    def switch_addhelper(self):
        if self.rhs:
            handler = self.account.search(self.rhs)
        else:
            handler = self.account
        evennia.GLOBAL_SCRIPTS.jobs.promote_account(self.account, self.lhs, handler, show_word="Helper",
                                                    rank=1, start_type=0)

    def switch_remhelper(self):
        if self.rhs:
            handler = self.account.search(self.rhs)
        else:
            handler = self.account
        evennia.GLOBAL_SCRIPTS.jobs.demote_account(self.account, self.lhs, handler, show_word="Helper",
                                                   rank=0, start_type=1)

    def switch_approve(self):
        pass

    def switch_deny(self):
        pass

    def switch_cancel(self):
        pass

    def switch_revive(self):
        pass

    def switch_due(self):
        pass

    def switch_move(self):
        evennia.GLOBAL_SCRIPTS.jobs.move_job(self.account, self.lhs, self.rhs)


class CmdJobList(JobCmd):
    key = "+jlist"
    switch_options = ['old', 'pending', 'brief', 'search', 'scan', 'next']

    def switch_pending(self):
        if self.lhs:
            buckets = [bucket for bucket in [evennia.GLOBAL_SCRIPTS.jobs.find_bucket(self.account, self.lhs), ] if bucket.jobs.filter(status=0).count() and bucket.access(self.account, "admin")]
        else:
            buckets = [bucket for bucket in evennia.GLOBAL_SCRIPTS.jobs.visible_buckets(self.account)
                       if bucket.jobs.filter(status=0).count() and bucket.access(self.account, "admin")]
        if not buckets:
            raise ValueError("No visible Pending jobs for applicable Job Buckets.")
        message = list()
        message.append(self.styled_header("Pending Jobs"))
        message.append(JOB_COLUMNS)
        for bucket in buckets:
            message.append(self.styled_separator(f"Pending for: {bucket} - {bucket.jobs.filter(status=0).count()} Total"))
            for j in bucket.jobs.filter(status=0).reverse()[:20]:
                message.append(j.display_line(self.account, admin=True))
        message.append(self.styled_footer(()))
        self.msg('\n'.join(message))

    def switch_scan(self):
        buckets = [bucket for bucket in evennia.GLOBAL_SCRIPTS.jobs.visible_buckets(self.account)
                   if bucket.access(self.account, "admin")]
        message = list()
        all_buckets = list()
        for bucket in buckets:
            pen_jobs = bucket.new(self.account)
            if pen_jobs:
                all_buckets.append((bucket, pen_jobs))
        if not all_buckets:
            raise ValueError("Nothing new to show!")
        for bucket, jobs in all_buckets:
            message.append(self.styled_separator(f'Job Activity - {bucket}'))
            for j in jobs:
                message.append(j.display_line(self.account, admin=True))
        message.append(self.styled_footer())
        self.msg('\n'.join(message))

    def switch_next(self):
        buckets = [bucket for bucket in evennia.GLOBAL_SCRIPTS.jobs.visible_buckets(self.account)
                   if bucket.access(self.account, "admin")]
        job = None
        for bucket in buckets:
            job = bucket.new(self.account).first()
            if job:
                break
        if not job:
            raise ValueError("Nothing new to show!")
        self.display_job(str(job.id))

    def switch_old(self):
        self.display_bucket(self.lhs, old=True)

    def switch_brief(self):
        pass

    def switch_search(self):
        pass


class CmdJob(JobCmd):
    key = '+job'
    aliases = ['+jobs', ]
    switch_options = ['reply', 'comment']

    def switch_reply(self):
        evennia.GLOBAL_SCRIPTS.jobs.create_comment(self.account, self.lhs, comment_text=self.rhs, comment_type=1)

    def switch_comment(self):
        evennia.GLOBAL_SCRIPTS.jobs.create_comment(self.account, self.lhs, comment_text=self.rhs, comment_type=2)


class CmdJRequest(JobCmd):
    key = '+jrequest'
    system_name = 'REQUEST'

    def switch_main(self):
        if not self.lhs:
            raise ValueError("No Bucket or Subject entered!")
        if '/' not in self.lhs:
            raise ValueError("Usage: +request <bucket>/<subject>=<text>")
        bucket, subject = self.lhs.split('/', 1)
        evennia.GLOBAL_SCRIPTS.jobs.create_job(self.account, bucket, subject, self.rhs)


class CmdMyJob(CmdJob):
    key = '+myjob'
    aliases = ['+myjobs']
    switch_options = ['reply', 'old', 'approve', 'deny', 'cancel', 'revive', 'comment', 'due', 'claim', 'unclaim',
                       'addhelper', 'remhelper']


JOB_COMMANDS = [CmdJBucket, CmdJob, CmdJobAdmin, CmdJobList, CmdMyJob, CmdJRequest]
