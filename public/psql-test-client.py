import psycopg2
from configparser import ConfigParser
import argparse

# sslrootcert=system
# sslmode=verify-full
# In this case sslmode specifies that SSL is required.
#
# To perform server certificate verification you can set sslmode to verify-full or verify-ca. You need to supply the path to the server certificate in sslrootcert. Also set the sslcert and sslkey values to your client certificate and key respectively.


# https://www.postgresqltutorial.com/postgresql-python/connect/
def config(filename='database.ini', section='postgresql'):
	# create a parser
	parser = ConfigParser()
	# read config file
	parser.read(filename)

	# get section, default to postgresql
	db = {}
	if parser.has_section(section):
		params = parser.items(section)
		for param in params:
			db[param[0]] = param[1]
	else:
		raise Exception('Section {0} not found in the {1} file'.format(section, filename))
	return db

if __name__ == "__main__":	
	conn = None
	try:
		# read connection parameters
		params = config()
		
		# connect to the PostgreSQL server
		print('Connecting to the PostgreSQL database...')
		conn = psycopg2.connect(**params)
		
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
		cur.execute("SELECT COUNT(*) FROM states")
                # 'SELECT COUNT(*) FROM states'
		count = cur.fetchone()
		print("Test Query: %s rows" % count)
			# close the communication with the PostgreSQL
		cur.close()
	except (Exception, psycopg2.DatabaseError) as error:
		print(error)
	finally:
		if conn is not None:
			conn.close()
			print('Database connection closed.')
