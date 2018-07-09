from setuptools import setup

setup(name='resume_importer',
      version='0.0.1',
      description='Riminder resume importer.',
      url='https://github.com/Riminder/riminder-resumes-importer',
      author='riminder',
      author_email='contact@rimider.net',
      license='MIT',
      install_requires=[
          'riminder==1.0.4'
      ],
      entry_points={
        'console_scripts': [
            'resumeImporter = resume_importer:main',
        ]
      },
      python_requires='>=3.5',
      zip_safe=False)
