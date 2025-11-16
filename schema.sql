CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  hash TEXT NOT NULL
);

CREATE TABLE results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT,
  summary TEXT,
  resources TEXT,
  ics BLOB,
  semester_start_date DATE,
  semester_end_date DATE,
  current_date DATE,
  FOREIGN KEY (user_id) REFERENCES users (id)
);