#!/usr/bin/env python3

import psycopg2
from configparser import ConfigParser
import argparse
import os

# sslrootcert=system
# sslmode=verify-full
# In this case sslmode specifies that SSL is required.
#
# To perform server certificate verification you can set sslmode to verify-full or verify-ca. You need to supply the path to the server certificate in sslrootcert. Also set the sslcert and sslkey values to your client certificate and key respectively.


# https://www.postgresqltutorial.com/postgresql-python/connect/
def configuration(defaults={'config':os.path.expanduser('~/.pg_service.conf'), 'section':'postgres'}):
	# create a parser
	parser = ConfigParser()
	# read config file
	parser.read(defaults['config'])
	# get section, default to postgresql
	if parser.has_section(defaults['section']):
		params = parser.items(defaults['section'])
		for param in params:
			defaults[param[0]] = param[1]
	else:
		raise Exception('Section {0} not found in the {1} file'.format(defaults['section'], defaults['config']))
	return defaults

if __name__ == "__main__":
	config = None
	defaults ={}
	defaults['config'] = os.path.expanduser('~/.pg_service.conf')
	defaults['section'] = os.getenv('PGSESSION', 'postgres')
	defaults['host'] = 'psql.domain.tld'
	defaults['port'] = 5432
	defaults['database'] = 'postgres'
	defaults['user'] = 'postgres'
	defaults['password'] = None
	defaults['sslmode'] = 'verify-full'
	defaults['sslcert'] = os.path.expanduser('~/.postgresql/client.cert')
	defaults['sslkey'] = os.path.expanduser('~/.postgresql/client.key')
	defaults['sslrootcert'] = os.path.expanduser('/etc/ssl/cert.pem')
	
	parser = argparse.ArgumentParser(description='Connect to PostgreSQL and run basic queries.')
	parser.add_argument('--config', type=str, default=defaults['config'], help='Path to database config file')
	parser.add_argument('--section', type=str, default=defaults['section'], help='Section name in config file (overrides PGSESSION)')
	try:
		config = configuration(defaults)
	except Exception as error:
		print(error)
	parser.add_argument('--host', type=str, default=config['host'], help='Host(fqdn or ip) to connect')
	parser.add_argument('--port', type=int, default=config['port'], help='Port(number) to connect')
	parser.add_argument('--database', type=str, default=config['database'], help='Database(name) to connect')
	parser.add_argument('--user', type=str, default=config['user'], help='User/role(name) to connect')
	parser.add_argument('--password', type=str, default=config['password'], help='User/role(credentials) to connect')
	parser.add_argument('--sslmode', type=str, default=config['sslmode'], help='SSL Mode - disable, require, verify, verify-full')
	parser.add_argument('--sslcert', type=str, default=config['sslcert'], help='SSL Certificate(file path) -- Certificate authorization certificate')
	parser.add_argument('--sslkey', type=str, default=config['sslkey'], help='SSL Private Key(file path) -- Certificate authorization private key')
	parser.add_argument('--sslrootcert', type=str, default=config['sslrootcert'], help='SSL Public Certificates(file path) -- OS certificate list')
	
	parser.add_argument('--sql', type=str, default="", help='SQL code to execute')

	args = parser.parse_args()
	config = vars(args)
	del config['config']
	del config['section']
	sql = config['sql']
	del config['sql']
	conn = None
	try:
		print(config)
		# connect to the PostgreSQL server
		print('Connecting to the PostgreSQL database...')
		conn = psycopg2.connect(**config)
		
		# create a cursor
		cur = conn.cursor()
		
		# execute a statement
		print('PostgreSQL database version:', end=" ")
		cur.execute('SELECT version()')
		# display the PostgreSQL database server version
		db_version = cur.fetchone()[0]
		print(db_version)
		print('PostgreSQL SSL:', end=" ")
		cur.execute('SHOW ssl')
		# display the PostgreSQL ssl
		db_ssl = cur.fetchone()[0]
		print(db_ssl)
		
		"""if 0 < len((sql):
			cur.execute(sql)  # 'SELECT COUNT(*) FROM states'
			count = cur.fetchone()
			print("Test Query: %s rows" % count)
		"""	# close the communication with the PostgreSQL
		cur.close()
	except (Exception, psycopg2.DatabaseError) as error:
		print(error)
	finally:
		if conn is not None:
			conn.close()
		print('Database connection closed.')
