using Aspire.Hosting.ApplicationModel;

var builder = DistributedApplication.CreateBuilder(args);

// Host folder that holds database files and logs
const string fsRoot = "/Users/sarath/workspace/2027/eshop/fs";

// Fixed passwords (from appsettings.Development.json) so persisted data dirs keep working across runs
var mysqlPassword = builder.AddParameter("mysql-password", secret: true);
var postgresPassword = builder.AddParameter("postgres-password", secret: true);
var supersetSecretKey = builder.AddParameter("superset-secret-key", secret: true);
var supersetAdminPassword = builder.AddParameter("superset-admin-password", secret: true);
var jupyterToken = builder.AddParameter("jupyter-token", secret: true);

var mysql = builder.AddMySql("mysql", password: mysqlPassword)
    .WithDataBindMount($"{fsRoot}/mysql/data")
    .WithBindMount($"{fsRoot}/mysql/logs", "/var/log/mysql")
    .WithArgs(
        "--log-error=/var/log/mysql/error.log",
        "--general-log=1", "--general-log-file=/var/log/mysql/general.log",
        "--slow-query-log=1", "--slow-query-log-file=/var/log/mysql/slow.log")
    .WithLifetime(ContainerLifetime.Persistent);
var mysqlDb = mysql.AddDatabase("contactsdb-mysql", "contacts");

var postgres = builder.AddPostgres("postgres", password: postgresPassword)
    .WithDataBindMount($"{fsRoot}/postgres/data")
    .WithBindMount($"{fsRoot}/postgres/logs", "/var/log/postgresql")
    .WithArgs(
        "-c", "logging_collector=on",
        "-c", "log_directory=/var/log/postgresql",
        "-c", "log_filename=postgres.log")
    .WithLifetime(ContainerLifetime.Persistent);
var postgresDb = postgres.AddDatabase("contactsdb-postgres", "contacts");
var supersetDb = postgres.AddDatabase("supersetdb", "superset");

var mysqlEndpoint = mysql.GetEndpoint("tcp");
var postgresEndpoint = postgres.GetEndpoint("tcp");

// Contacts -> MySQL; users + analytics -> PostgreSQL. Connection details passed as plain env vars.
// Superset: metadata in PostgreSQL ("superset" db); connect to the "contacts" databases from the UI
// (MySQL: mysql+pymysql://root:<pw>@mysql:3306/contacts, Postgres: postgresql://postgres:<pw>@postgres:5432/contacts)
builder.AddDockerfile("superset", "../superset")
    .WithHttpEndpoint(port: 8088, targetPort: 8088, name: "http")
    .WithEnvironment("SUPERSET_SECRET_KEY", supersetSecretKey)
    .WithEnvironment("SUPERSET_ADMIN_PASSWORD", supersetAdminPassword)
    .WithEnvironment("POSTGRES_HOST", postgresEndpoint.Property(EndpointProperty.Host))
    .WithEnvironment("POSTGRES_PORT", postgresEndpoint.Property(EndpointProperty.Port))
    .WithEnvironment("POSTGRES_USER", "postgres")
    .WithEnvironment("POSTGRES_PASSWORD", postgresPassword)
    .WithEnvironment("POSTGRES_DATABASE", "superset")
    .WaitFor(supersetDb)
    .WithExternalHttpEndpoints();

// Jupyter: notebooks persisted on the host; DB connection details provided as env vars
builder.AddDockerfile("jupyter", "../jupyter")
    .WithHttpEndpoint(port: 8889, targetPort: 8888, name: "http")
    .WithBindMount($"{fsRoot}/jupyter/work", "/home/jovyan/work")
    .WithEnvironment("JUPYTER_TOKEN", jupyterToken)
    .WithEnvironment("MYSQL_HOST", mysqlEndpoint.Property(EndpointProperty.Host))
    .WithEnvironment("MYSQL_PORT", mysqlEndpoint.Property(EndpointProperty.Port))
    .WithEnvironment("MYSQL_USER", "root")
    .WithEnvironment("MYSQL_PASSWORD", mysqlPassword)
    .WithEnvironment("MYSQL_DATABASE", "contacts")
    .WithEnvironment("POSTGRES_HOST", postgresEndpoint.Property(EndpointProperty.Host))
    .WithEnvironment("POSTGRES_PORT", postgresEndpoint.Property(EndpointProperty.Port))
    .WithEnvironment("POSTGRES_USER", "postgres")
    .WithEnvironment("POSTGRES_PASSWORD", postgresPassword)
    .WithEnvironment("POSTGRES_DATABASE", "contacts")
    .WaitFor(mysqlDb)
    .WaitFor(postgresDb)
    .WithExternalHttpEndpoints();

var api = builder.AddUvicornApp("api", "../api", "main:app")
    .WithEnvironment("MYSQL_HOST", mysqlEndpoint.Property(EndpointProperty.Host))
    .WithEnvironment("MYSQL_PORT", mysqlEndpoint.Property(EndpointProperty.Port))
    .WithEnvironment("MYSQL_USER", "root")
    .WithEnvironment("MYSQL_PASSWORD", mysqlPassword)
    .WithEnvironment("MYSQL_DATABASE", "contacts")
    .WithEnvironment("POSTGRES_HOST", postgresEndpoint.Property(EndpointProperty.Host))
    .WithEnvironment("POSTGRES_PORT", postgresEndpoint.Property(EndpointProperty.Port))
    .WithEnvironment("POSTGRES_USER", "postgres")
    .WithEnvironment("POSTGRES_PASSWORD", postgresPassword)
    .WithEnvironment("POSTGRES_DATABASE", "contacts")
    .WaitFor(mysqlDb)
    .WaitFor(postgresDb)
    .WithExternalHttpEndpoints()
    .WithHttpHealthCheck("/health");

builder.AddUvicornApp("frontend", "../frontend", "main:app")
    .WithReference(api)
    .WaitFor(api)
    .WithExternalHttpEndpoints();

builder.Build().Run();
