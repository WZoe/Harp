DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS host;
DROP TABLE IF EXISTS organization;
DROP TABLE IF EXISTS orderer;

CREATE TABLE user
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT        NOT NULL,
    usertype INTEGER(1)  NOT NULL,
--  0 - admin; 1 - normal user;
    org_id   INTEGER,
    FOREIGN KEY (org_id) REFERENCES organization (id)
);

CREATE TABLE host
(
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ip   TEXT UNIQUE NOT NULL,
    user TEXT        NOT NULL,
    port INTEGER
);

CREATE TABLE organization
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    orgname     TEXT UNIQUE NOT NULL,
    host_id     INTEGER     NOT NULL,
    api_port    INTEGER     NOT NULL,
    daemon_port INTEGER     NOT NULL,
    FOREIGN KEY (host_id) REFERENCES host (id)
);

CREATE TABLE orderer
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    host_id     INTEGER     NOT NULL,
    daemon_port INTEGER     NOT NULL,
    FOREIGN KEY (host_id) references host (id)
)


