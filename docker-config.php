<?php  // Moodle configuration file — ENV-driven (no hardcoded secrets)

unset($CFG);
global $CFG;
$CFG = new stdClass();

$CFG->dbtype    = 'pgsql';
$CFG->dblibrary = 'native';
$CFG->dbhost    = getenv('MOODLE_DB_HOST')    ?: 'postgres';
$CFG->dbname    = getenv('MOODLE_DB_NAME')    ?: 'moodle';
$CFG->dbuser    = getenv('MOODLE_DB_USER')    ?: 'moodleuser';
$CFG->dbpass    = getenv('MOODLE_DB_PASSWORD') ?: 'changeme';
$CFG->prefix    = 'mdl_';
$CFG->dboptions = array(
    'dbpersist' => 0,
    'dbport'    => getenv('MOODLE_DB_PORT') ?: 5432,
    'dbsocket'  => '',
);

$CFG->wwwroot   = getenv('MOODLE_WWWROOT')  ?: 'http://localhost:8082';
$CFG->dataroot  = '/var/www/moodledata';
$CFG->admin     = 'admin';

$CFG->directorypermissions = 0777;

require_once(__DIR__ . '/lib/setup.php');

// There is no php closing tag in this file,
// it is intentional because it prevents trailing whitespace problems!
