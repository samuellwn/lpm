-- The MIT License (MIT)
-- Copyright (c) 2016 Samuel Loewen <samuellwn@samuellwn.org>

-- Permission is hereby granted, free of charge, to any person
-- obtaining a copy of this software and associated documentation
-- files (the "Software"), to deal in the Software without
-- restriction, including without limitation the rights to use, copy,
-- modify, merge, publish, distribute, sublicense, and/or sell copies
-- of the Software, and to permit persons to whom the Software is
-- furnished to do so, subject to the following conditions:

-- The above copyright notice and this permission notice shall be
-- included in all copies or substantial portions of the Software.

-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
-- EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
-- MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
-- NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
-- BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
-- ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
-- CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
-- SOFTWARE.

-- The database format version specifier. Used to aid in backwards
-- compatibility.
create table format_version (
    version integer primary key
);

insert into format_version values (1);

-- Package master table.
create table packages (
    package package primary key,
    status text not null
);

-- Contains the build environment for installed packages. This build
-- environment is used for building packages that depend on other
-- packages we are tracking.
create table build_env (
    package package not null, -- package to modify env of
    variable text not null, -- variable to modify
    value text not null,
    mode text not null, -- how to modify (append, prepend, or overwrite)
    sep text, -- separator used when appending or prepending
    primary key (package, variable, value),
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);

-- Similar to the build environment package but contains the
-- environment used when running package binaries.
create table run_env (
    package package not null,
    variable text not null,
    value text not null,
    mode text not null,
    sep text,
    primary key (package, variable, value),
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);

create table dependancies (
    package package not null,
    dependancy package not null,
    primary key (package, depandancy),
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);

create table bindirs (
    package package not null,
    dir path not null,
    primary key (package, dir),
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);

create table libdirs (
    package package not null,
    dir path not null,
    primary key (package, dir),
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);

create table binaries (
    package package not null,
    binary path not null,
    primary key (package, path)
    foreign key (package)
        references packages(package)
        on update cascade -- should not be needed
        on delete cascade
);
