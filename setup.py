import setuptools

with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name='django-advanced-report-builder',
    version='1.0.1',
    author='Thomas Turner',
    description='Django app that allows you to build reports from modals',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/django-advance-utils/django-advanced-report-builder',
    include_package_data=True,
    packages=['advanced_report_builder'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'Django >= 3.2',
        'django-filtered-datatables >= 0.0.21',
        'django-ajax-helpers >= 0.0.20',
        'django-nested-modals >= 0.0.21',
        'time-stamped-model >= 0.2.3',
        'date-offset >= 0.0.2',
    ],
)
