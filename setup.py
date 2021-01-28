from setuptools import setup, find_packages

packages = ['hvi2_script']
print('packages: {}'.format(packages))

setup(name="hvi2_script",
	version="0.2",
	packages = find_packages(),
	install_requires=[
          # 'keysight_hvi>=1.0.17'
      ],
	)
