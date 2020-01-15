INSTALLED_APPS = ["athanor_job"]

GLOBAL_SCRIPTS = dict()

GLOBAL_SCRIPTS['job'] = {
    'typeclass': 'athanor_job.controllers.AthanorJobManager',
    'repeats': -1, 'interval': 60, 'desc': 'Job API for Job System',
    'locks': "admin:perm(Admin)",
}
