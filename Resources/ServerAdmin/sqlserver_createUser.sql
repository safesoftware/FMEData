/* *============================================================================

   Name     : sqlserver_createUser.sql

   System   : FME Server

   Language : SQL

   Purpose  : Create the FME Server database user and permissions.

   Author               Date            Changes made
   ------------------   ------------    -------------------------------
   Hieu Nguyen          May 14, 2008    Original
   Jeffrey Cheung       July 14, 2009   Fixed database ownership issue


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

USE fmeserver;
GO

CREATE LOGIN fmeserver WITH PASSWORD = '$FME$1ser$ver', DEFAULT_DATABASE = fmeserver;
GO

CREATE USER fmeserver FOR LOGIN fmeserver;
GO

GRANT CONTROL, TAKE OWNERSHIP, ALTER, EXECUTE, INSERT, DELETE, UPDATE, SELECT, REFERENCES, VIEW DEFINITION TO fmeserver;
GO

EXEC sp_addrolemember N'db_owner', N'fmeserver';
GO
