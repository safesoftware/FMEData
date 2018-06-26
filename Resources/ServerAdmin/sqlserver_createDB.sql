/* *============================================================================

   Name     : sqlserver_createDB.sql

   System   : FME Server

   Language : SQL

   Purpose  : Create the FME Server database schema.

   Author               Date            Changes made
   ------------------   ------------    -------------------------------
   David Roper          Jul 27, 2007    Original Creation
   Hieu Nguyen          Apr 14, 2008    Compatibility updates


                  Copyright (c) 2005 - 2014, Safe Software Inc.
                              All Rights Reserved

    This software may not be copied or reproduced, in all or in part,
    without the prior written consent of Safe Software Inc.

    The entire risk as to the results and performance of the software,
    supporting text and other information contained in this file
    (collectively called the "Software") is with the user.
    In no event will Safe Software Incorporated be liable for damages,
    including loss of profits or consequential damages, arising out of
    the use of the Software.


============================================================================ **/

CREATE DATABASE fmeserver;
GO

USE fmeserver;

/*
 * ================================================
 * ===            REPOSITORY TABLES             ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_repositoryinfo (
   repositoryinfo_id INTEGER NOT NULL IDENTITY,
   name NVARCHAR(255) NOT NULL,
   description NTEXT,
   PRIMARY KEY(repositoryinfo_id),
   UNIQUE (name)
);

/* ------------------------------------------------
 * filetype (0 = workspace, 1 = customformat, 2 = customtransformer, 3 = template)
 */
CREATE TABLE fme_item (
   item_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   repositoryinfo_id INTEGER NOT NULL,
   name NVARCHAR(255) NOT NULL,
   version INTEGER,
   title NVARCHAR(255),
   description NTEXT,
   filesize BIGINT,
   category NVARCHAR(50),
   requirements NTEXT,
   requirementskeyword NVARCHAR(50),
   useage NTEXT,
   history NTEXT,
   lastsavedate NVARCHAR(30),
   lastsavebuild NVARCHAR(60),
   buildnum INTEGER,
   legaltermsconditions NTEXT,
   guid NVARCHAR(60),
   is_deprecated BIT,
   priorguids NTEXT,
   filetype INTEGER,
   username NVARCHAR(255),
   lastpublishdate DATETIME,
   UNIQUE (repositoryinfo_id, name, version),
   FOREIGN KEY(repositoryinfo_id)
      REFERENCES fme_repositoryinfo(repositoryinfo_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_item1 ON fme_item(filetype);
CREATE INDEX fme_item2 ON fme_item(username);

/* ------------------------------------------------
 * filetype (0 = workspace, 1 = customformat, 2 = customtransformer, 3 = template)
 */
CREATE TABLE fme_item_version (
   item_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   repositoryinfo_id INTEGER NOT NULL,
   name NVARCHAR(255) NOT NULL,
   version INTEGER,
   title NVARCHAR(255),
   description NTEXT,
   filesize BIGINT,
   category NVARCHAR(50),
   requirements NTEXT,
   requirementskeyword NVARCHAR(50),
   useage NTEXT,
   history NTEXT,
   lastsavedate NVARCHAR(30),
   lastsavebuild NVARCHAR(60),
   buildnum INTEGER,
   legaltermsconditions NTEXT,
   guid NVARCHAR(60),
   is_deprecated BIT,
   priorguids NTEXT,
   filetype INTEGER,
   username NVARCHAR(255),
   lastpublishdate DATETIME,
   UNIQUE (repositoryinfo_id, name, version),
   FOREIGN KEY(repositoryinfo_id)
      REFERENCES fme_repositoryinfo(repositoryinfo_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_item_version1 ON fme_item_version(filetype);

/* ------------------------------------------------
 */
CREATE TABLE fme_item_res (
   item_res_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   item_id INTEGER NOT NULL,
   name NVARCHAR(255) NOT NULL,
   description NTEXT,
   filesize BIGINT,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_item_res1 ON fme_item_res(item_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_parameter (
   parameter_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   item_id INTEGER NOT NULL,
   name NVARCHAR(255),
   description NTEXT,
   default_val NTEXT,
   param_type NVARCHAR(255),
   options_type NVARCHAR(255),
   options NTEXT,
   is_optional BIT,
   guiline NTEXT,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_parameter1 ON fme_parameter(item_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_dataset (
   dataset_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   item_id INTEGER NOT NULL,
   name NVARCHAR(255),
   location NTEXT,
   format NVARCHAR(255),
   is_source BIT,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_dataset1 ON fme_dataset(item_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_feature_type (
   feature_type_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   dataset_id INTEGER NOT NULL,
   name NVARCHAR(255),
   description NTEXT,
   FOREIGN KEY(dataset_id)
      REFERENCES fme_dataset(dataset_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_feature_type1 ON fme_feature_type(dataset_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_attribute (
   attribute_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   feature_type_id INTEGER NOT NULL,
   name NTEXT,
   fme_type NTEXT,
   width INTEGER,
   decimals INTEGER,
   FOREIGN KEY(feature_type_id)
      REFERENCES fme_feature_type(feature_type_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_attribute1 ON fme_attribute(feature_type_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_featuretype_props (
   featuretype_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   feature_type_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(feature_type_id)
      REFERENCES fme_feature_type(feature_type_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_featuretype_props1 ON fme_featuretype_props(feature_type_id);
CREATE INDEX fme_featuretype_props2 ON fme_featuretype_props(feature_type_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_dataset_props (
   dataset_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   dataset_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(dataset_id)
      REFERENCES fme_dataset(dataset_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_dataset_props1 ON fme_dataset_props(dataset_id);
CREATE INDEX fme_dataset_props2 ON fme_dataset_props(dataset_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_item_props (
   item_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   item_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_item_props1 ON fme_item_props(item_id);
CREATE INDEX fme_item_props2 ON fme_item_props(item_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_service (
   service_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   name NVARCHAR(255) NOT NULL,
   display_name NVARCHAR(255),
   description NTEXT,
   url_pattern NTEXT,
   is_enabled BIT,
   is_allowworkspacereg BIT,
   is_allowcustomformatreg BIT,
   is_allowcustomtransformreg BIT,
   is_allowtemplatereg BIT,
   UNIQUE (name)
);

CREATE INDEX fme_service1 ON fme_service(display_name);

/* ------------------------------------------------
 */
CREATE TABLE fme_service_props (
   service_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   service_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(service_id)
      REFERENCES fme_service(service_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_service_props1 ON fme_service_props(service_id);
CREATE INDEX fme_service_props2 ON fme_service_props(service_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_item_service (
   service_id INTEGER NOT NULL,
   item_id INTEGER NOT NULL,
   PRIMARY KEY(service_id, item_id),
   FOREIGN KEY(service_id)
      REFERENCES fme_service(service_id)
         ON DELETE CASCADE,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_item_service1 ON fme_item_service(item_id);
CREATE INDEX fme_item_service2 ON fme_item_service(service_id);

/* ------------------------------------------------
 */
CREATE TABLE fme_favorite_item (
   username NVARCHAR(255),
   item_id INTEGER NOT NULL,
   PRIMARY KEY(username, item_id),
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_favorite_item1 ON fme_favorite_item(username);

GO

/*
 * ================================================
 * ===            JOB TABLES                    ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_jobs (
   job_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   date_queued DATETIME2 NOT NULL,
   date_started DATETIME2 DEFAULT NULL,
   date_finished DATETIME2 DEFAULT NULL,
   job_status INTEGER NOT NULL,
   description NTEXT,
   num_retries INTEGER NOT NULL,
   keyword NVARCHAR(255) NOT NULL,
   request NTEXT NOT NULL,
   priority INTEGER NOT NULL,
   datequeuedhash BIGINT NOT NULL,
   ttl INTEGER,
   ttc INTEGER,
   rtc BIT,
   tag NVARCHAR(255),
   notifmsg NTEXT,
   result NTEXT,
   client_result_port INTEGER,
   client_result_host NVARCHAR(255),
   engine_instance NVARCHAR(255),
   engine_host NVARCHAR(255),
   owner NVARCHAR(255),
   username NVARCHAR(255),
   result_mode INTEGER NOT NULL,
   enginemgr_host NVARCHAR(255),
   context_id NVARCHAR(60)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_job_history (
   job_id INTEGER NOT NULL PRIMARY KEY,
   date_queued DATETIME2 NOT NULL,
   date_started DATETIME2 DEFAULT NULL,
   date_finished DATETIME2 DEFAULT NULL,
   job_status INTEGER NOT NULL,
   description NTEXT,
   num_retries INTEGER NOT NULL,
   keyword NVARCHAR(255) NOT NULL,
   request NTEXT NOT NULL,
   priority INTEGER NOT NULL,
   datequeuedhash BIGINT NOT NULL,
   ttl INTEGER,
   ttc INTEGER,
   rtc BIT,
   tag NVARCHAR(255),
   notifmsg NTEXT,
   result NTEXT,
   client_result_port INTEGER,
   client_result_host NVARCHAR(255),
   engine_instance NVARCHAR(255),
   engine_host NVARCHAR(255),
   owner NVARCHAR(255),
   username NVARCHAR(255),
   result_mode INTEGER NOT NULL,
   enginemgr_host NVARCHAR(255),
   context_id NVARCHAR(60)
);

CREATE INDEX fme_job_history1 ON fme_job_history(date_finished DESC);
CREATE INDEX fme_job_history2 ON fme_job_history(username);

GO

/*
 * ================================================
 * ===         SCHEDULING TABLES                ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_schedule_task (
    schedule_task_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    category NVARCHAR(100) NOT NULL,
    name NVARCHAR(220) NOT NULL,
    description NTEXT,
    username NVARCHAR(220),
    userroles NTEXT,
    transformation_request NTEXT,
    starttime DATETIME NOT NULL,
    endtime DATETIME,
    cronexpression NVARCHAR(255),
    intervalunit NVARCHAR(10),
    repeatinterval INTEGER,
    is_enabled BIT,
    nid NVARCHAR(320) NOT NULL,
    UNIQUE (category, name)
);

CREATE INDEX fme_schedule_task1 ON fme_schedule_task(starttime);

GO

/*
 * ================================================
 * ===         CORE SECURITY TABLES             ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_useraccount (
    useraccount_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    username NVARCHAR(220) NOT NULL,
    userpassword NVARCHAR(220),
    fullname NVARCHAR(255),
    email NVARCHAR(255),
    is_enabled BIT,
    is_sharingenabled BIT,
    UNIQUE (username)
);

CREATE INDEX fme_useraccount1 ON fme_useraccount(username, userpassword);

/* ------------------------------------------------
 */
CREATE TABLE fme_usertoken (
   usertoken_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   username NVARCHAR(255) NOT NULL,
   token NVARCHAR(255) NOT NULL,
   clientid NVARCHAR(255),
   expirationtimeout INTEGER NOT NULL,
   expirationdate DATETIME NOT NULL,
   firsttokendate DATETIME NOT NULL,
   lasttokendate DATETIME NOT NULL,
   UNIQUE (username),
   UNIQUE (token)
);


/* ------------------------------------------------
 */
CREATE TABLE fme_role (
    role_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_useraccount_assigned_role (
    useraccount_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY(useraccount_id, role_id),
    FOREIGN KEY(useraccount_id)
       REFERENCES fme_useraccount(useraccount_id)
          ON DELETE CASCADE,
    FOREIGN KEY(role_id)
       REFERENCES fme_role(role_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_category (
    category_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255),
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_appresource (
    appresource_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255),
    clientid NVARCHAR(255),
    category_id INTEGER NOT NULL,
    owner NVARCHAR(255),
    UNIQUE (category_id, name),
	 FOREIGN KEY(category_id)
       REFERENCES fme_category(category_id)
          ON DELETE CASCADE,
);

CREATE INDEX fme_appresource1 ON fme_appresource(clientid);
CREATE INDEX fme_appresource2 ON fme_appresource(category_id);

/* ------------------------------------------------
 * type 2 denotes category permission. type 1 denotes resource permission.
 */
CREATE TABLE fme_permission (
    permission_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255),
    type INTEGER NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_category_permission (
    category_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY(category_id, permission_id),
    FOREIGN KEY(category_id)
       REFERENCES fme_category(category_id)
          ON DELETE CASCADE,
    FOREIGN KEY(permission_id)
       REFERENCES fme_permission(permission_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_appresource_assigned_role (
    appresource_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY(appresource_id, permission_id, role_id),
    FOREIGN KEY(appresource_id)
       REFERENCES fme_appresource(appresource_id)
          ON DELETE CASCADE,
    FOREIGN KEY(role_id)
       REFERENCES fme_role(role_id)
          ON DELETE CASCADE,
    FOREIGN KEY(permission_id)
       REFERENCES fme_permission(permission_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_category_assigned_role (
    category_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY(category_id, role_id, permission_id),
    FOREIGN KEY(category_id)
       REFERENCES fme_category(category_id)
          ON DELETE CASCADE,
    FOREIGN KEY(role_id)
       REFERENCES fme_role(role_id)
          ON DELETE CASCADE,
    FOREIGN KEY(permission_id)
       REFERENCES fme_permission(permission_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_action (
    action_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_permission_assigned_action (
    permission_id INTEGER NOT NULL,
    action_id INTEGER NOT NULL,
    PRIMARY KEY(permission_id, action_id),
    FOREIGN KEY(permission_id)
       REFERENCES fme_permission(permission_id)
          ON DELETE CASCADE,
    FOREIGN KEY(action_id)
       REFERENCES fme_action(action_id)
          ON DELETE CASCADE
);

CREATE TABLE fme_ldap_server (
    ldap_server_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    host NVARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    encryption NVARCHAR(255) NOT NULL,
    authentication NVARCHAR(255) NOT NULL,
    user_name NVARCHAR(MAX) NOT NULL,
    password NVARCHAR(MAX) NOT NULL,
    last_sync DATETIME,
    last_updated BIGINT NOT NULL,
    UNIQUE(name)
);

CREATE TABLE fme_ldap_server_property (
    fme_ldap_server_property_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    ldap_server_id INTEGER NOT NULL,
    property NVARCHAR(255) NOT NULL,
    value NVARCHAR(MAX) NOT NULL,
    FOREIGN KEY (ldap_server_id)
        REFERENCES fme_ldap_server(ldap_server_id)
            ON DELETE CASCADE
);

CREATE TABLE fme_ldap_user (
    useraccount_id INTEGER NOT NULL PRIMARY KEY,
    ldap_server_id INTEGER NOT NULL,
    dn NVARCHAR(MAX) NOT NULL,
    authId NVARCHAR(MAX) NOT NULL,
    FOREIGN KEY(useraccount_id)
        REFERENCES fme_useraccount(useraccount_id)
            ON DELETE CASCADE,
    FOREIGN KEY(ldap_server_id)
        REFERENCES fme_ldap_server(ldap_server_id)
            ON DELETE CASCADE
);

CREATE TABLE fme_ldap_role (
    role_id INTEGER NOT NULL PRIMARY KEY,
    ldap_server_id INTEGER NOT NULL,
    dn NVARCHAR(MAX) NOT NULL,
    FOREIGN KEY(role_id)
        REFERENCES fme_role(role_id)
            ON DELETE CASCADE,
    FOREIGN KEY(ldap_server_id)
        REFERENCES fme_ldap_server(ldap_server_id)
            ON DELETE CASCADE
);

GO

/* ------------------------------------------------
 * Insert security values for suitable defaults
 */

/* ------------------------------------------------
 */
INSERT INTO fme_role VALUES ('fmeadmin');
INSERT INTO fme_role VALUES ('fmesuperuser');
INSERT INTO fme_role VALUES ('user:admin');

/* ------------------------------------------------
 * admin -> ec0f44e2e2b20538dc4be4cadb6ab98239d6a270
 */
INSERT INTO fme_useraccount VALUES ('admin', 'ec0f44e2e2b20538dc4be4cadb6ab98239d6a270', 'Administrator', '', 1, 1);

/* ------------------------------------------------
 * Assign roles to account.
 */
INSERT INTO fme_useraccount_assigned_role VALUES (1, 1);
INSERT INTO fme_useraccount_assigned_role VALUES (1, 2);
INSERT INTO fme_useraccount_assigned_role VALUES (1, 3);

GO

/*
 * ================================================
 * ===            NOTIFICATION TABLES           ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_topic (
    topic_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    description NTEXT,
    UNIQUE (name)
);

/*
 * =====================
 * === SUBSCRIPTIONS
 * =====================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_subscriber (
    subscriber_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255) NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_subscriber_props (
   subscriber_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   subscriber_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(subscriber_id)
      REFERENCES fme_subscriber(subscriber_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_subscriber_props1 ON fme_subscriber_props(subscriber_id);
CREATE INDEX fme_subscriber_props2 ON fme_subscriber_props(subscriber_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_subscription (
    subscription_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    subscriber_id INTEGER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    UNIQUE (name),
    FOREIGN KEY(subscriber_id)
      REFERENCES fme_subscriber(subscriber_id)
         ON DELETE CASCADE

);

/* ------------------------------------------------
 */
CREATE TABLE fme_subscription_topic (
    subscription_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    type INTEGER NOT NULL,
    PRIMARY KEY(subscription_id, topic_id, type),
    FOREIGN KEY(subscription_id)
       REFERENCES fme_subscription(subscription_id)
          ON DELETE CASCADE,
    FOREIGN KEY(topic_id)
       REFERENCES fme_topic(topic_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_subscription_props (
   subscription_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   subscription_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(subscription_id)
      REFERENCES fme_subscription(subscription_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_subscription_props1 ON fme_subscription_props(subscription_id);
CREATE INDEX fme_subscription_props2 ON fme_subscription_props(subscription_id, category);

GO

/*
 * =====================
 * === PUBLICATIONS
 * =====================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_publisher (
    publisher_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255) NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_publisher_props (
   publisher_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   publisher_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(publisher_id)
      REFERENCES fme_publisher(publisher_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_publisher_props1 ON fme_publisher_props(publisher_id);
CREATE INDEX fme_publisher_props2 ON fme_publisher_props(publisher_id, category);

/* ------------------------------------------------
 */
CREATE TABLE fme_publication (
    publication_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    publisher_id INTEGER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    UNIQUE (name),
    FOREIGN KEY(publisher_id)
      REFERENCES fme_publisher(publisher_id)
         ON DELETE CASCADE

);

/* ------------------------------------------------
 */
CREATE TABLE fme_publication_topic (
    publication_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    type INTEGER NOT NULL,
    PRIMARY KEY(publication_id, topic_id, type),
    FOREIGN KEY(publication_id)
       REFERENCES fme_publication(publication_id)
          ON DELETE CASCADE,
    FOREIGN KEY(topic_id)
       REFERENCES fme_topic(topic_id)
          ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_publication_props (
   publication_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   publication_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NVARCHAR(1000),
   propattribs NVARCHAR(1000),
   FOREIGN KEY(publication_id)
      REFERENCES fme_publication(publication_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_publication_props1 ON fme_publication_props(publication_id);
CREATE INDEX fme_publication_props2 ON fme_publication_props(publication_id, category);

GO

/*
 * ================================================
 * ===         DEPLOYMENT NODE TABLES           ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_deployment (
    deployment_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255),
    description NTEXT,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_node (
    node_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255),
    description NTEXT,
    host NVARCHAR(255),
    coreadminport INTEGER NOT NULL,
    engineadminport INTEGER NOT NULL,
    version INTEGER NOT NULL,
    UNIQUE (name)
);

/* ------------------------------------------------
 */
CREATE TABLE fme_registerednodes (
    deployment_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    PRIMARY KEY(deployment_id, node_id),
    FOREIGN KEY(deployment_id)
      REFERENCES fme_deployment(deployment_id)
         ON DELETE CASCADE,
    FOREIGN KEY(node_id)
      REFERENCES fme_node(node_id)
         ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_processconfig (
    node_id INTEGER NOT NULL,
    name NVARCHAR(255),
    description NTEXT,
    type NVARCHAR(50) NOT NULL,
    execparams NTEXT,
    monitoringparams NTEXT,
    startcommand NTEXT,
    stopcommand NTEXT,
    startorder INTEGER NOT NULL,
    stoporder INTEGER NOT NULL,
    version INTEGER NOT NULL,
    UNIQUE (node_id, name),
    FOREIGN KEY(node_id)
      REFERENCES fme_node(node_id)
         ON DELETE CASCADE
);

GO

/* ------------------------------------------------
 * Set the deployment name
 */

INSERT INTO fme_deployment VALUES ('FME Server', 'FME Server Default Deployment');

GO

/*
 * ================================================
 * ===           QUEUE NODE TABLES              ===
 * ================================================
 */

CREATE TABLE fme_queue_nodes (
    node_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    host NVARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    is_active BIT,
    failover_order INTEGER NOT NULL,
    UNIQUE (name),
    UNIQUE (host, port)
);

CREATE INDEX fme_queue_node1 ON fme_queue_nodes(name);

GO

/*
 * ================================================
 * ===           CLEANUP TASK TABLES            ===
 * ================================================
 */

CREATE TABLE fme_cleanup_task (
    cleanup_task_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    category NVARCHAR(100) NOT NULL,
    name NVARCHAR(220) NOT NULL,
    description NTEXT,
    is_enabled BIT,
    sourcelocator NTEXT,
    destlocator NTEXT,
    filefilter NVARCHAR(255),
    maxfileage INTEGER,
    maxjobage INTEGER,
    compressfiles BIT,
    type INTEGER,
    UNIQUE (category, name)
);

CREATE TABLE fme_cleanup_config (
    cleanup_config_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    watchinterval INTEGER,
    taskinterval INTEGER,
    warningnotiftopic NVARCHAR(255),
    warningmindisksizegb INTEGER,
    warningmindisksizepct INTEGER,
    warningop NVARCHAR(8),
    criticalnotiftopic NVARCHAR(255),
    criticalmindisksizegb INTEGER,
    criticalmindisksizepct INTEGER,
    criticalop NVARCHAR(8),
    UNIQUE (name)
);

GO

INSERT INTO fme_cleanup_config VALUES ('Default', 300, 86400, '', 20, 20, 'AND', '', 10, 10, 'AND');

GO

/*
 * ================================================
 * ===        SHARED RESOURCE TABLES            ===
 * ================================================
 */

/* ------------------------------------------------
 */
CREATE TABLE fme_sharedres_type (
    sharedrestype_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    UNIQUE (name)
);

GO

INSERT INTO fme_sharedres_type VALUES ('FILE');
INSERT INTO fme_sharedres_type VALUES ('AWS_S3');
INSERT INTO fme_sharedres_type VALUES ('NETWORK');

/* ------------------------------------------------
 */
CREATE TABLE fme_sharedres (
    sharedres_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
    sharedrestype_id INTEGER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    display_name NVARCHAR(255) NOT NULL,
    description NTEXT,
    is_migratable BIT,
    is_updatable BIT,
    UNIQUE (name),
    FOREIGN KEY(sharedrestype_id)
      REFERENCES fme_sharedres_type(sharedrestype_id)
         ON DELETE CASCADE
);

/* ------------------------------------------------
 */
CREATE TABLE fme_sharedres_props (
   sharedres_props_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   sharedres_id INTEGER NOT NULL,
   category NVARCHAR(255),
   propname NVARCHAR(255),
   propvalue NTEXT,
   propattribs NTEXT,
   FOREIGN KEY(sharedres_id)
      REFERENCES fme_sharedres(sharedres_id)
         ON DELETE CASCADE
);

CREATE INDEX fme_sharedres_props1 ON fme_sharedres_props(sharedres_id);
CREATE INDEX fme_sharedres_props2 ON fme_sharedres_props(sharedres_id, category);

GO

/*
 * ================================================
 * ===        NAMED CONNECTION TABLES           ===
 * ================================================
 */

CREATE TABLE fme_nc_namedconnections (
   ncid INTEGER NOT NULL IDENTITY PRIMARY KEY,
   connectionname NVARCHAR(230) NOT NULL,
   connectionType INTEGER NOT NULL,
   servicename NVARCHAR(780) ,
   username NVARCHAR(220) ,
   UNIQUE (connectionname, username) );

CREATE TABLE fme_nc_keyvalues (
   field NVARCHAR(440) NOT NULL,
   value NVARCHAR(780),
   ncid INTEGER NOT NULL,
   PRIMARY KEY(ncid, field) ,
   FOREIGN KEY(ncid)
      REFERENCES fme_nc_namedconnections(ncid)
         ON DELETE CASCADE);

CREATE TABLE fme_nc_webservices(
   servicename NVARCHAR(225) NOT NULL PRIMARY KEY,
   sourceservicename NVARCHAR(225),
   servicexml NTEXT NOT NULL,
   UNIQUE(servicename, sourceservicename) );

CREATE TABLE fme_nc_version  (
   versionnum INTEGER NOT NULL PRIMARY KEY  );

GO

/*
 * ================================================
 * ===        PROJECTS TABLES                   ===
 * ================================================
 */

CREATE TABLE fme_projects (
   project_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   name NVARCHAR(255) NOT NULL,
   description NTEXT,
   readme NTEXT,
   version NVARCHAR(16),
   lastsavedate DATETIME NOT NULL,
   username NVARCHAR(255) NOT NULL,
   UNIQUE (name)
);

CREATE INDEX fme_projects2 ON fme_projects(username);

CREATE TABLE fme_project_projects (
   parent_project_id INTEGER NOT NULL,
   child_project_id INTEGER NOT NULL,
   PRIMARY KEY (parent_project_id, child_project_id),
   FOREIGN KEY(parent_project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   CONSTRAINT fme_proj_proj1 CHECK (parent_project_id<>child_project_id)
);

CREATE TABLE fme_project_repositories (
   project_id INTEGER NOT NULL,
   repository_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, repository_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(repository_id)
      REFERENCES fme_repositoryinfo(repositoryinfo_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_repository_items (
   project_id INTEGER NOT NULL,
   item_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, item_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(item_id)
      REFERENCES fme_item(item_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_schedule_tasks (
   project_id INTEGER NOT NULL,
   schedule_task_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, schedule_task_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(schedule_task_id)
      REFERENCES fme_schedule_task(schedule_task_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_topics (
   project_id INTEGER NOT NULL,
   topic_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, topic_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(topic_id)
      REFERENCES fme_topic(topic_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_subscriptions (
   project_id INTEGER NOT NULL,
   subscription_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, subscription_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(subscription_id)
      REFERENCES fme_subscription(subscription_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_publications (
   project_id INTEGER NOT NULL,
   publication_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, publication_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(publication_id)
      REFERENCES fme_publication(publication_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_shared_resources (
   project_id INTEGER NOT NULL,
   sharedres_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, sharedres_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(sharedres_id)
      REFERENCES fme_sharedres(sharedres_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_shared_res_paths (
   project_sharedres_path_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   project_id INTEGER NOT NULL,
   sharedres_id INTEGER NOT NULL,
   path NTEXT NOT NULL,
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(sharedres_id)
      REFERENCES fme_sharedres(sharedres_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_cleanup_tasks (
   project_id INTEGER NOT NULL,
   cleanup_task_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, cleanup_task_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(cleanup_task_id)
      REFERENCES fme_cleanup_task(cleanup_task_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_named_connections (
   project_id INTEGER NOT NULL,
   ncid INTEGER NOT NULL,
   PRIMARY KEY (project_id, ncid),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(ncid)
      REFERENCES fme_nc_namedconnections(ncid)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_user_accounts (
   project_id INTEGER NOT NULL,
   useraccount_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, useraccount_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(useraccount_id)
      REFERENCES fme_useraccount(useraccount_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_project_roles (
   project_id INTEGER NOT NULL,
   role_id INTEGER NOT NULL,
   PRIMARY KEY (project_id, role_id),
   FOREIGN KEY(project_id)
      REFERENCES fme_projects(project_id)
         ON DELETE CASCADE,
   FOREIGN KEY(role_id)
      REFERENCES fme_role(role_id)
         ON DELETE CASCADE
);

GO

/*
 * ================================================
 * ===        TAGS TABLES                       ===
 * ================================================
 */

CREATE TABLE fme_tags (
   tag_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   name NVARCHAR(255) NOT NULL,
   description NTEXT,
   priority INTEGER NOT NULL,
   UNIQUE (name)
);

CREATE TABLE fme_default_tag(
   default_tag_limit INTEGER NOT NULL DEFAULT 1 PRIMARY KEY,
   default_tag_id INTEGER NOT NULL,
   CONSTRAINT CHK_singlerow CHECK (default_tag_limit = 1),
   FOREIGN KEY(default_tag_id)
         REFERENCES fme_tags(tag_id)
            ON DELETE CASCADE
);

CREATE TABLE fme_repository_tags (
   repository_id INTEGER NOT NULL PRIMARY KEY,
   tag_id INTEGER NOT NULL,
   FOREIGN KEY(repository_id)
      REFERENCES fme_repositoryinfo(repositoryinfo_id)
         ON DELETE CASCADE,
   FOREIGN KEY(tag_id)
      REFERENCES fme_tags(tag_id)
         ON DELETE CASCADE
);

CREATE TABLE fme_engine_tags(
   engine_instance NVARCHAR(255),
   tag_id INTEGER NOT NULL,
   PRIMARY KEY (engine_instance, tag_id),
   FOREIGN KEY(tag_id)
      REFERENCES fme_tags(tag_id)
         ON DELETE CASCADE
);

GO

INSERT INTO fme_tags VALUES ('Default', 'Default', 5);
INSERT INTO fme_default_tag (default_tag_id) VALUES (1);

GO

/*
 * ================================================
 * ===    VERSION CONTROL CONFIGURATION TABLE   ===
 * ================================================
 */

CREATE TABLE fme_version_control (
   remote_url NVARCHAR(255),
   remote_token NTEXT,
   is_enabled BIT
);

GO

/*
 * ================================================
 * ==      VERSION CONTROL COMMITS TABLE        ===
 * ================================================
 */

CREATE TABLE fme_commits (
   commit_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   commit_sha VARCHAR(40) NOT NULL,
   repository_name NVARCHAR(255) NOT NULL,
   item_name NVARCHAR(255) NOT NULL,
   committer NVARCHAR(255) NOT NULL,
   time DATETIME2 NOT NULL,
   commit_message NTEXT NOT NULL
);

CREATE INDEX fme_commits3 ON fme_commits(repository_name);
CREATE INDEX fme_commits4 ON fme_commits(item_name);

GO

/*
 * ================================================
 * ===        MIGRATION TABLES                  ===
 * ================================================
 */

CREATE TABLE fme_migration_jobs (
   job_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
   job_type INTEGER NOT NULL,
   content_type INTEGER NOT NULL,
   date_started DATETIME NOT NULL,
   date_finished DATETIME DEFAULT NULL,
   status INTEGER NOT NULL,
   request NTEXT NOT NULL,
   result NTEXT,
   username NVARCHAR(255) NOT NULL,
   host VARCHAR(255)
);

CREATE INDEX fme_migration_jobs1 ON fme_migration_jobs(date_finished DESC);
CREATE INDEX fme_migration_jobs2 ON fme_migration_jobs(status);
CREATE INDEX fme_migration_jobs3 ON fme_migration_jobs(username);

GO

/*
 * ================================================
 * ===        QUARTZ SCHEDULER TABLES           ===
 * ================================================
 */

CREATE TABLE FME_QRTZ_JOB_DETAILS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  JOB_NAME NVARCHAR(220) NOT NULL,
  JOB_GROUP NVARCHAR(100) NOT NULL,
  DESCRIPTION NVARCHAR(250) NULL,
  JOB_CLASS_NAME NVARCHAR(250) NOT NULL,
  IS_DURABLE NVARCHAR(1) NOT NULL,
  IS_NONCONCURRENT NVARCHAR(1) NOT NULL,
  IS_UPDATE_DATA NVARCHAR(1) NOT NULL,
  REQUESTS_RECOVERY NVARCHAR(1) NOT NULL,
  JOB_DATA IMAGE NULL,
  PRIMARY KEY (SCHED_NAME,JOB_NAME,JOB_GROUP)
);

CREATE TABLE FME_QRTZ_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  TRIGGER_NAME NVARCHAR(220) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  JOB_NAME NVARCHAR(220) NOT NULL,
  JOB_GROUP NVARCHAR(100) NOT NULL,
  DESCRIPTION NVARCHAR(250) NULL,
  NEXT_FIRE_TIME BIGINT NULL,
  PREV_FIRE_TIME BIGINT NULL,
  PRIORITY INTEGER NULL,
  TRIGGER_STATE NVARCHAR(16) NOT NULL,
  TRIGGER_TYPE NVARCHAR(8) NOT NULL,
  START_TIME BIGINT NOT NULL,
  END_TIME BIGINT NULL,
  CALENDAR_NAME NVARCHAR(200) NULL,
  MISFIRE_INSTR SMALLINT NULL,
  JOB_DATA IMAGE NULL,
  PRIMARY KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP),
  FOREIGN KEY (SCHED_NAME,JOB_NAME,JOB_GROUP)
    REFERENCES FME_QRTZ_JOB_DETAILS(SCHED_NAME,JOB_NAME,JOB_GROUP)
      ON DELETE CASCADE
);

CREATE TABLE FME_QRTZ_SIMPLE_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  TRIGGER_NAME NVARCHAR(220) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  REPEAT_COUNT BIGINT NOT NULL,
  REPEAT_INTERVAL BIGINT NOT NULL,
  TIMES_TRIGGERED BIGINT NOT NULL,
  PRIMARY KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP),
  FOREIGN KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
    REFERENCES FME_QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
      ON DELETE CASCADE
);

CREATE TABLE FME_QRTZ_CRON_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL ,
  TRIGGER_NAME NVARCHAR(220) NOT NULL ,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL ,
  CRON_EXPRESSION NVARCHAR(120) NOT NULL ,
  TIME_ZONE_ID NVARCHAR(80),
  PRIMARY KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP),
  FOREIGN KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
    REFERENCES FME_QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
      ON DELETE CASCADE
);

CREATE TABLE FME_QRTZ_SIMPROP_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  TRIGGER_NAME NVARCHAR(220) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  STR_PROP_1 NVARCHAR(512) NULL,
  STR_PROP_2 NVARCHAR(512) NULL,
  STR_PROP_3 NVARCHAR(512) NULL,
  INT_PROP_1 INT NULL,
  INT_PROP_2 INT NULL,
  LONG_PROP_1 BIGINT NULL,
  LONG_PROP_2 BIGINT NULL,
  DEC_PROP_1 NUMERIC(13,4) NULL,
  DEC_PROP_2 NUMERIC(13,4) NULL,
  BOOL_PROP_1 NVARCHAR(1) NULL,
  BOOL_PROP_2 NVARCHAR(1) NULL,
  PRIMARY KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP),
  FOREIGN KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
    REFERENCES FME_QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
      ON DELETE CASCADE
);

CREATE TABLE FME_QRTZ_BLOB_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  TRIGGER_NAME NVARCHAR(220) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  BLOB_DATA IMAGE NULL,
  PRIMARY KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP),
  FOREIGN KEY (SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
    REFERENCES FME_QRTZ_TRIGGERS(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP)
      ON DELETE CASCADE
);

CREATE TABLE FME_QRTZ_CALENDARS (
  SCHED_NAME NVARCHAR(60) NOT NULL ,
  CALENDAR_NAME NVARCHAR(200) NOT NULL ,
  CALENDAR IMAGE NOT NULL,
  PRIMARY KEY (SCHED_NAME,CALENDAR_NAME)
);

CREATE TABLE FME_QRTZ_PAUSED_TRIGGER_GRPS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  PRIMARY KEY (SCHED_NAME,TRIGGER_GROUP)
);

CREATE TABLE FME_QRTZ_FIRED_TRIGGERS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  ENTRY_ID NVARCHAR(95) NOT NULL,
  TRIGGER_NAME NVARCHAR(220) NOT NULL,
  TRIGGER_GROUP NVARCHAR(100) NOT NULL,
  INSTANCE_NAME NVARCHAR(200) NOT NULL,
  FIRED_TIME BIGINT NOT NULL,
  SCHED_TIME BIGINT NOT NULL,
  PRIORITY INTEGER NOT NULL,
  STATE NVARCHAR(16) NOT NULL,
  JOB_NAME NVARCHAR(220) NULL,
  JOB_GROUP NVARCHAR(100) NULL,
  IS_NONCONCURRENT NVARCHAR(1) NULL,
  REQUESTS_RECOVERY NVARCHAR(1) NULL,
  PRIMARY KEY (SCHED_NAME,ENTRY_ID)
);

CREATE TABLE FME_QRTZ_SCHEDULER_STATE (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  INSTANCE_NAME NVARCHAR(200) NOT NULL,
  LAST_CHECKIN_TIME BIGINT NOT NULL,
  CHECKIN_INTERVAL BIGINT NOT NULL,
  PRIMARY KEY (SCHED_NAME,INSTANCE_NAME)
);

CREATE TABLE FME_QRTZ_LOCKS (
  SCHED_NAME NVARCHAR(60) NOT NULL,
  LOCK_NAME NVARCHAR(40) NOT NULL,
  PRIMARY KEY (SCHED_NAME,LOCK_NAME)
);

create index idx_qrtz_j_req_recovery on fme_qrtz_job_details(SCHED_NAME,REQUESTS_RECOVERY);
create index idx_qrtz_j_grp on fme_qrtz_job_details(SCHED_NAME,JOB_GROUP);

create index idx_qrtz_t_j on fme_qrtz_triggers(SCHED_NAME,JOB_NAME,JOB_GROUP);
create index idx_qrtz_t_jg on fme_qrtz_triggers(SCHED_NAME,JOB_GROUP);
create index idx_qrtz_t_c on fme_qrtz_triggers(SCHED_NAME,CALENDAR_NAME);
create index idx_qrtz_t_g on fme_qrtz_triggers(SCHED_NAME,TRIGGER_GROUP);
create index idx_qrtz_t_state on fme_qrtz_triggers(SCHED_NAME,TRIGGER_STATE);
create index idx_qrtz_t_n_state on fme_qrtz_triggers(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP,TRIGGER_STATE);
create index idx_qrtz_t_n_g_state on fme_qrtz_triggers(SCHED_NAME,TRIGGER_GROUP,TRIGGER_STATE);
create index idx_qrtz_t_next_fire_time on fme_qrtz_triggers(SCHED_NAME,NEXT_FIRE_TIME);
create index idx_qrtz_t_nft_st on fme_qrtz_triggers(SCHED_NAME,TRIGGER_STATE,NEXT_FIRE_TIME);
create index idx_qrtz_t_nft_misfire on fme_qrtz_triggers(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME);
create index idx_qrtz_t_nft_st_misfire on fme_qrtz_triggers(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_STATE);
create index idx_qrtz_t_nft_st_misfire_grp on fme_qrtz_triggers(SCHED_NAME,MISFIRE_INSTR,NEXT_FIRE_TIME,TRIGGER_GROUP,TRIGGER_STATE);

create index idx_qrtz_ft_trig_inst_name on fme_qrtz_fired_triggers(SCHED_NAME,INSTANCE_NAME);
create index idx_qrtz_ft_inst_job_req_rcvry on fme_qrtz_fired_triggers(SCHED_NAME,INSTANCE_NAME,REQUESTS_RECOVERY);
create index idx_qrtz_ft_j_g on fme_qrtz_fired_triggers(SCHED_NAME,JOB_NAME,JOB_GROUP);
create index idx_qrtz_ft_jg on fme_qrtz_fired_triggers(SCHED_NAME,JOB_GROUP);
create index idx_qrtz_ft_t_g on fme_qrtz_fired_triggers(SCHED_NAME,TRIGGER_NAME,TRIGGER_GROUP);
create index idx_qrtz_ft_tg on fme_qrtz_fired_triggers(SCHED_NAME,TRIGGER_GROUP);

GO

/*
 * ================================================
 * ===        PASSWORD RESET TABLE             ===
 * ================================================
 */

CREATE TABLE fme_password_reset (
   is_enabled BIT,
   public_url NTEXT
);

GO

/*
 * ================================================
 * ===           AUTOMATION TABLES              ===
 * ================================================
 */

CREATE TABLE fme_automation (
    id UNIQUEIDENTIFIER PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    created DATETIME NOT NULL,
    updated DATETIME NOT NULL,
    is_enabled BIT
);

CREATE TABLE fme_automation_tag (
    id UNIQUEIDENTIFIER NOT NULL,
    tag NVARCHAR(255) NOT NULL,
    PRIMARY KEY (id, tag),
    FOREIGN KEY (id)
        REFERENCES fme_automation(id)
            ON DELETE CASCADE
);

CREATE TABLE fme_automation_node (
    id UNIQUEIDENTIFIER NOT NULL,
    node_id UNIQUEIDENTIFIER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    description NTEXT,
    node_type NVARCHAR(16) NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    PRIMARY KEY (id, node_id),
    FOREIGN KEY (id)
        REFERENCES fme_automation(id)
            ON DELETE CASCADE
);

CREATE TABLE fme_automation_port (
    id UNIQUEIDENTIFIER NOT NULL,
    node_id UNIQUEIDENTIFIER NOT NULL,
    port_id UNIQUEIDENTIFIER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    PRIMARY KEY (id, node_id, port_id),
    FOREIGN KEY (id, node_id)
        REFERENCES fme_automation_node(id, node_id)
            ON DELETE CASCADE
);

CREATE TABLE fme_automation_parameter (
    id UNIQUEIDENTIFIER NOT NULL,
    node_id UNIQUEIDENTIFIER NOT NULL,
    name NVARCHAR(255) NOT NULL,
    value NVARCHAR(255) NOT NULL,
    PRIMARY KEY (id, node_id, name),
    FOREIGN KEY (id, node_id)
        REFERENCES fme_automation_node(id, node_id)
            ON DELETE CASCADE
);

CREATE TABLE fme_automation_link (
    id UNIQUEIDENTIFIER NOT NULL,
    link_id UNIQUEIDENTIFIER NOT NULL,
    from_port_id UNIQUEIDENTIFIER NOT NULL,
    to_port_id UNIQUEIDENTIFIER NOT NULL,
    PRIMARY KEY (id, link_id),
    FOREIGN KEY (id)
        REFERENCES fme_automation(id)
            ON DELETE CASCADE
);

GO

/*
 * ================================================
 * ===              OAUTHV1 TABLES              ===
 * ================================================
 */

CREATE TABLE fme_oauthvone (
    request_oauth_token NVARCHAR(255) NOT NULL,
    request_oauth_secret NTEXT NOT NULL,
    connectionname NTEXT NOT NULL,
    return_uri NTEXT NOT NULL,
    expirationdate BIGINT NOT NULL,
    UNIQUE(request_oauth_token)
);

GO

/*
 * ================================================
 * ===        LOCK TABLES                       ===
 * ================================================
 */

CREATE TABLE fme_lock (
  lock_key NVARCHAR(100) NOT NULL,
  val NVARCHAR(100) NOT NULL,
  uuid NVARCHAR(100) NOT NULL,
  expiry BIGINT NOT NULL,
  UNIQUE(lock_key)
);

/*
 * ================================================
 * ===        CORE NODE TABLES                  ===
 * ================================================
 */
CREATE TABLE fme_core_node (
  core_node_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
  name NVARCHAR(255) NOT NULL,
  modifieddate DATETIME NOT NULL,
  expirydate DATETIME NOT NULL,
  status NTEXT,
  timeout INTEGER NOT NULL,
  expiry BIGINT NOT NULL,
  is_leader BIT NOT NULL,
  numengines INTEGER NOT NULL,
  router_queuenodename NVARCHAR(255),
  job_queuenodename NVARCHAR(255),
  UNIQUE (name)
);

CREATE TABLE fme_config_node (
  config_node_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
  name NVARCHAR(255) NOT NULL,
  modifieddate DATETIME NOT NULL,
  expirydate DATETIME NOT NULL,
  status NTEXT,
  timeout INTEGER NOT NULL,
  expiry BIGINT NOT NULL,
  is_leader BIT NOT NULL,
  UNIQUE (name)
);

CREATE TABLE fme_publisher_node (
  publisher_node_id INTEGER NOT NULL IDENTITY PRIMARY KEY,
  name NVARCHAR(255) NOT NULL,
  modifieddate DATETIME NOT NULL,
  expirydate DATETIME NOT NULL,
  status NTEXT,
  timeout INTEGER NOT NULL,
  expiry BIGINT NOT NULL,
  is_leader BIT NOT NULL,
  UNIQUE (name)
);

/*
 * ================================================
 * ===        CONFIG TABLES                     ===
 * ================================================
 */
CREATE TABLE fme_config (
  config_key NVARCHAR(100) NOT NULL,
  val NTEXT,
  UNIQUE(config_key)
);

GO

INSERT INTO fme_config VALUES ('pause_queue_incoming', 'NO');
INSERT INTO fme_config VALUES ('pause_queue_outgoing', 'NO');
INSERT INTO fme_config VALUES ('subscribers_enabled', 'YES');
INSERT INTO fme_config VALUES ('post_install_init', 'NO');

GO
