import re
from evennia.locks.lockhandler import LockException
from athanor.core.scripts import AthanorGlobalScript
from athanor.jobs.models import BucketDB, JobDB
from athanor.utils.text import partial_match
from evennia.utils.validatorfuncs import duration, unsigned_integer, lock


_RE_BUCKET = re.compile(r"^[a-zA-Z]{3,8}$")

_JOB_LINK_KIND = {0: 'Opened', 1: 'Replied', 2: '|rSTAFF COMMENTED|n', 3: 'Moved', 4: 'Approved',
                5: 'Denied', 6: 'Canceled', 7: 'Revived', 8: 'Appointed Handler', 9: 'Appointed Helper',
                10: 'Removed Handler', 11: 'Removed Helper', 12: 'Due Date Changed'}


class JobManager(AthanorGlobalScript):
    system_name = 'JOB'
    option_dict = {
        'bucket_locks': ('Default locks to use for new Buckets', 'Lock', 'see:all();post:all();admin:perm(Admin) or perm(Job_Admin)'),
        'bucket_due': ('Default due duration for new Buckets.', 'Duration', 604800),
    }

    def buckets(self):
        return BucketDB.objects.filter_family().order_by('db_key')

    def visible_buckets(self, account):
        return [b for b in self.buckets() if b.access(account, 'see')]

    def create_bucket(self, account, name=None, description=None):
        if not self.access(account, 'admin'):
            raise ValueError("Permission denied!")
        if not _RE_BUCKET.match(name):
            raise ValueError("Buckets must be 3-8 alphabetical characters!")
        if BucketDB.objects.filter(key__iexact=name).exists():
            raise ValueError("Name is already in use.")
        new_bucket = BucketDB.objects.create(key=name, lock_storage=self.options.bucket_locks,
                                              due=self.options.bucket_due, description=description)
        new_bucket.save()
        announce = f"Bucket Created: {new_bucket.key}"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)
        return new_bucket

    def find_bucket(self, account, bucket=None):
        if isinstance(bucket, BucketDB):
            return bucket
        if not bucket:
            raise ValueError("Must enter a bucket name!")
        found = partial_match(bucket, self.visible_buckets(account))
        if not found:
            raise ValueError("Bucket not found.")
        return found

    def delete_bucket(self, account, bucket_name=None):
        if not account.is_superuser:
            raise ValueError("Permission denied. Superuser only.")
        bucket = self.find_bucket(account, bucket_name)
        if not bucket_name.lower() == bucket.key.lower():
            raise ValueError("Must enter the exact name for a deletion!")
        announce = f"Bucket '{bucket}' |rDELETED|n!"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)
        bucket.delete()

    def lock_bucket(self, account, bucket=None, locks=None):
        if not account.is_superuser:
            raise ValueError("Permission denied. Superuser only.")
        bucket = self.find_bucket(account, bucket)
        new_locks = lock(locks, option_key='Job Bucket Locks',
                         access_options=['see', 'post', 'admin'])
        try:
            bucket.locks.add(new_locks)
            bucket.save(update_fields=['lock_storage'])
        except LockException as e:
            raise ValueError(str(e))
        announce = f"Bucket '{bucket}' locks changed to: {new_locks}"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)

    def rename_bucket(self, account, bucket=None, new_name=None):
        if not self.access(account, 'admin'):
            raise ValueError("Permission denied!")
        bucket = self.find_bucket(account, bucket)
        if not _RE_BUCKET.match(new_name):
            raise ValueError("Buckets must be 3-8 alphabetical characters!")
        if BucketDB.objects.filter(key__iexact=new_name).exclude(id=bucket.id).exists():
            raise ValueError("Name is already in use.")
        old_name = bucket.key
        bucket.key = new_name
        bucket.save(update_fields=['key', ])
        announce = f"Bucket '{old_name}' renamed to: {new_name}"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)

    def describe_bucket(self, account, bucket=None, description=None):
        if not self.access(account, 'admin'):
            raise ValueError("Permission denied!")
        bucket = self.find_bucket(account, bucket)
        if not description:
            raise ValueError("Must provide a description!")
        bucket.description = description
        bucket.save(update_fields=['description', ])
        announce = f"Bucket '{bucket}' description changed!"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)

    def due_bucket(self, account, bucket=None, new_due=None):
        if not self.access(account, 'admin'):
            raise ValueError("Permission denied!")
        bucket = self.find_bucket(account, bucket)
        new_due = duration(new_due, option_key='Job Bucket Due Duration')
        old_due = bucket.due
        bucket.due = new_due
        bucket.save(update_fields=['due', ])
        announce = f"Bucket '{bucket}' due duration changed from {old_due} to {new_due}"
        self.alert(announce, enactor=account)
        self.msg_target(announce, account)

    def create_job(self, account, bucket=None, subject=None, opening=None):
        bucket = self.find_bucket(account, bucket)
        if not bucket.access(account, 'post'):
            raise ValueError("Permission denied.")
        if not subject:
            raise ValueError("Must enter a subject!")
        if not opening:
            raise ValueError("Must enter opening statement!")
        job = bucket.make_job(account, title=subject, opening=opening)
        return job

    def find_job(self, account, job=None, check_access=True):
        if isinstance(job, JobDB):
            return job
        job_id = unsigned_integer(job, option_key='Job ID')
        found = JobDB.objects.filter(id=job_id).first()
        if not found:
            raise ValueError("Job not found!")
        if not check_access:
            return found
        if found.bucket.access(account, 'admin'):
            return found
        if found.links.filter(account_stub=account.stub, link_type__gt=0).exists():
            return found

        raise ValueError("Permission denied.")

    def promote_account(self, account, job=None, target_account=None, show_word="Handler", rank=2, start_type=2):
        results = self.change_link_type(account, job, target_account, link_type=rank, show_word=show_word, start_type=start_type)
        job = results.job
        announce = f"{account} appointed a new new {show_word}: {target_account}"
        job.announce(announce)
        comment_mode = 8 if rank == 2 else 9
        job.make_comment(account, comment_mode, text=announce)
        return job

    def demote_account(self, account, job=None, target_account=None, show_word="Handler", rank=0, start_type=2):
        results = self.change_link_type(account, job, target_account, link_type=rank, start_type=start_type, show_word=show_word)
        job = results.job
        announce = f"{account} removed a {show_word}: {target_account}"
        job.announce(announce)
        comment_mode = 10 if start_type == 2 else 11
        job.make_comment(account, comment_mode, text=announce)
        return job

    def change_link_type(self, account, job=None, target_account=None, link_type=None, start_type=None, show_word=None):
        job = self.find_job(account, job)
        if not job.bucket.access(account, "admin"):
            raise ValueError("Permission denied.")
        link, created = job.links.get_or_create(account_stub=target_account.stub)
        if start_type and link.link_type != start_type:
            raise ValueError(f"{target_account} is not a {show_word}!")
        if link_type not in (0, 1, 2, 3):
            raise ValueError("Invalid link type value!")
        if link_type > 0 and start_type is not None:
            if link.link_type != start_type:
                raise ValueError("Must first demote this account before changing account status.")
        link.link_type = link_type
        link.save()
        return link

    def move_job(self, account, job=None, destination=None):
        job = self.find_job(account, job)
        old_bucket = job.bucket
        if not old_bucket.access(self.account, "admin"):
            raise ValueError("Permission denied.")
        destination = self.find_bucket(account, destination)
        if not destination.access(self.account, "admin"):
            raise ValueError("Permission denied.")
        announce = f'{account} moved job to: {destination}'
        job.bucket = destination
        job.save(update_fields=['bucket', ])
        job.make_comment(account=account, comment_mode=3, text='%s to %s' % (old_bucket, destination))

    def change_job_status(self, account, job=None, new_status=None):
        job = self.find_job(account, job)

    def change_attn(self, account, job=None, new_attn=None):
        job = self.find_job(account, job)

    def create_comment(self, account, job=None, comment_text=None, comment_type=None, announce=True):
        job = self.find_job(account, job)
        bucket_admin = job.bucket.access(self.account, "admin")
        if not (bucket_admin or job.links.filter(account_stub=account.stub, link_type__gt=0).exists()):
            raise ValueError("Permission denied.")
        if not comment_text:
            raise ValueError("No text provided! What do you have to say?")
        if comment_type == 2 and not bucket_admin:
            raise ValueError("Comments may only created by staff.")
        private = True if comment_type == 2 else False
        return job.make_comment(account, comment_mode=comment_type, text=comment_text, is_private=private)
