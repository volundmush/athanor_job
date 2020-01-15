from django.db import models
from evennia.typeclasses.models import TypedObject


class BucketDB(TypedObject):
    __settingclasspath__ = "features.jobs.jobs.DefaultBucket"
    __defaultclasspath__ = "features.jobs.jobs.DefaultBucket"
    __applabel__ = "jobs"

    db_due = models.DurationField()
    db_description = models.TextField(blank=True, null=True)


    class Meta:
        verbose_name = 'Bucket'
        verbose_name_plural = 'Buckets'


class JobDB(TypedObject):
    __settingclasspath__ = "features.jobs.jobs.DefaultJob"
    __defaultclasspath__ = "features.jobs.jobs.DefaultJob"
    __applabel__ = "jobs"

    db_bucket = models.ForeignKey(BucketDB, related_name='jobs', on_delete=models.CASCADE)
    db_date_created = models.DateTimeField('creation date', editable=True, auto_now_add=True)
    db_date_due = models.DateTimeField(null=False)
    db_date_closed = models.DateTimeField(null=True)
    db_status = models.SmallIntegerField(default=0)
    # Status: 0 = Pending. 1 = Approved. 2 = Denied. 3 = Canceled
    db_date_public_update = models.DateTimeField(null=True)
    db_date_admin_update = models.DateTimeField(null=True)



    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'


class JobLinkDB(TypedObject):
    __settingclasspath__ = "features.jobs.jobs.DefaultJobLink"
    __defaultclasspath__ = "features.jobs.jobs.DefaultJobLink"
    __applabel__ = "jobs"

    db_account = models.ForeignKey('accounts.AccountDB', related_name='job_handling', on_delete=models.PROTECT)
    db_character = models.ForeignKey('objects.ObjectDB', related_name='job_handling', on_delete=models.PROTECT)
    db_job = models.ForeignKey(JobDB, related_name='links', on_delete=models.CASCADE)
    db_link_type = models.PositiveSmallIntegerField(default=0)
    db_date_checked = models.DateTimeField(null=True)

    class Meta:
        verbose_name = 'JobLink'
        verbose_name_plural = 'JobLinks'
        unique_together = (("db_account", "db_character", "db_job"),)




class JobCommentDB(TypedObject):
    __settingclasspath__ = "features.jobs.jobs.DefaultJobComment"
    __defaultclasspath__ = "features.jobs.jobs.DefaultJobComment"
    __applabel__ = "jobs"

    db_date_created = models.DateTimeField('creation date', editable=True, auto_now_add=True)
    db_link = models.ForeignKey(JobLinkDB, related_name='comments', on_delete=models.CASCADE)
    db_text = models.TextField(blank=True, null=True, default=None)
    db_is_private = models.BooleanField(default=False)
    db_comment_mode = models.PositiveSmallIntegerField(default=1)
    # Comment Mode: 0 = Opening. 1 = Reply. 2 = Staff Comment. 3 = Moved. 4 = Approved.
    # 5 = Denied. 6 = Canceled. 7 = Revived. 8 = Appoint Handler. 9 = Appoint Helper.
    # 10 = Removed Handler. 11 = Removed Helper. 12 = Due Date Changed

    class Meta:
        verbose_name = 'JobComment'
        verbose_name_plural = 'JobComments'


