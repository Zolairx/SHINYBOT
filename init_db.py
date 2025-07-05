import sqlite3

conn = sqlite3.connect('shinybot.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS shiny (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nom_pokemon TEXT NOT NULL,
    preuve TEXT,
    jeu TEXT,
    full_odds BOOLEAN,
    methode TEXT,
    charme_chroma BOOLEAN,
    sandwich_am BOOLEAN,
    switch2 BOOLEAN,
    points INTEGER,
    UNIQUE(user_id, nom_pokemon)
)
''')

conn.commit()
conn.close()

print("Base de données shinybot.db initialisée ✅")
