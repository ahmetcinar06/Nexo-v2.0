import sqlite3
from config import db

skills = [ (_,) for _ in (['Python', 'SQL', 'API', 'Discord'])]
statuses = [ (_,) for _ in (['Prototip Oluşturma', 'Geliştirme Aşamasında', 'Tamamlandı, kullanıma hazır', 'Güncellendi', 'Tamamlandı, ancak bakımı yapılmadı'])]

class DB_Manager:
    def __init__(self, database):
        self.database = database
        
    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS projects (
                            project_id INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            project_name TEXT NOT NULL,
                            description TEXT,
                            screenshots TEXT,
                            url TEXT,
                            status_id INTEGER,
                            FOREIGN KEY(status_id) REFERENCES status(status_id)
                        )''') 
            conn.execute('''CREATE TABLE IF NOT EXISTS skills (
                            skill_id INTEGER PRIMARY KEY,
                            skill_name TEXT
                        )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS project_skills (
                            project_id INTEGER,
                            skill_id INTEGER,
                            FOREIGN KEY(project_id) REFERENCES projects(project_id),
                            FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
                        )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS status (
                            status_id INTEGER PRIMARY KEY,
                            status_name TEXT
                        )''')
            conn.commit()

    def ensure_screenshots_column(self):
        """Add screenshots column to projects table if it doesn't exist."""
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.execute("PRAGMA table_info(projects)")
            cols = [row[1] for row in cur.fetchall()]
            if 'screenshots' not in cols:
                conn.execute("ALTER TABLE projects ADD COLUMN screenshots TEXT")
                conn.commit()

    def set_screenshots(self, project_id, screenshots):
        """Set screenshots for a project. `screenshots` can be a list or a JSON/string."""
        import json
        if isinstance(screenshots, (list, tuple)):
            val = json.dumps(screenshots)
        else:
            val = str(screenshots)
        sql = 'UPDATE projects SET screenshots = ? WHERE project_id = ?'
        self.__executemany(sql, [(val, project_id)])

    def add_screenshot(self, project_id, filename):
        """Append a screenshot filename to a project's screenshots list."""
        import json
        res = self.__select_data('SELECT screenshots FROM projects WHERE project_id = ?', (project_id,))
        current = []
        if res and res[0][0]:
            try:
                current = json.loads(res[0][0])
            except Exception:
                current = [res[0][0]]
        current.append(filename)
        self.set_screenshots(project_id, current)

    def add_status(self, status_name):
        """Insert a new status into the status table (ignore if exists)."""
        sql = 'INSERT OR IGNORE INTO status(status_name) VALUES(?)'
        self.__executemany(sql, [(status_name,)])

    def add_skill_name(self, skill_name):
        """Insert a new skill into the skills table (ignore if exists)."""
        sql = 'INSERT OR IGNORE INTO skills(skill_name) VALUES(?)'
        self.__executemany(sql, [(skill_name,)])

    def update_status(self, old_name, new_name):
        """Update status name."""
        sql = 'UPDATE status SET status_name = ? WHERE status_name = ?'
        self.__executemany(sql, [(new_name, old_name)])

    def update_skill_name(self, old_name, new_name):
        """Update skill name."""
        sql = 'UPDATE skills SET skill_name = ? WHERE skill_name = ?'
        self.__executemany(sql, [(new_name, old_name)])

    def __executemany(self, sql, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(sql, data)
            conn.commit()
    
    def __select_data(self, sql, data = tuple()):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(sql, data)
            return cur.fetchall()
        
    def default_insert(self):
        sql = 'INSERT OR IGNORE INTO skills (skill_name) values(?)'
        data = skills
        self.__executemany(sql, data)
        sql = 'INSERT OR IGNORE INTO status (status_name) values(?)'
        data = statuses
        self.__executemany(sql, data)


    def insert_project(self, data):
        sql = """INSERT INTO projects 
                (user_id, project_name, url, status_id) 
                values(?, ?, ?, ?)"""
        self.__executemany(sql, data)


    def insert_skill(self, user_id, project_name, skill):
        sql = 'SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?'
        project_id = self.__select_data(sql, (project_name, user_id))[0][0]
        skill_id = self.__select_data('SELECT skill_id FROM skills WHERE skill_name = ?', (skill,))[0][0]
        data = [(project_id, skill_id)]
        sql = 'INSERT OR IGNORE INTO project_skills VALUES(?, ?)'
        self.__executemany(sql, data)


    def get_statuses(self):
        sql="SELECT status_name from status"
        return self.__select_data(sql)
        

    def get_status_id(self, status_name):
        sql = 'SELECT status_id FROM status WHERE status_name = ?'
        res = self.__select_data(sql, (status_name,))
        if res: return res[0][0]
        else: return None

    def get_projects(self, user_id):
        sql="""SELECT * FROM projects 
            WHERE user_id = ?"""
        return self.__select_data(sql, data = (user_id,))
        
    def get_project_id(self, project_name, user_id):
        return self.__select_data(sql='SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?  ', data = (project_name, user_id,))[0][0]
        
    def get_skills(self):
        return self.__select_data(sql='SELECT * FROM skills')
    
    def get_project_skills(self, project_name):
        res = self.__select_data(sql='''SELECT skill_name FROM projects 
JOIN project_skills ON projects.project_id = project_skills.project_id 
JOIN skills ON skills.skill_id = project_skills.skill_id 
WHERE project_name = ?''', data = (project_name,) )
        return ', '.join([x[0] for x in res])
    
    def get_project_info(self, user_id, project_name):
        sql = """
SELECT project_name, description, url, status_name FROM projects
JOIN status ON status.status_id = projects.status_id
WHERE project_name=? AND user_id=?
"""
        # note: method signature is (user_id, project_name) but the SQL WHERE expects (project_name, user_id)
        return self.__select_data(sql=sql, data = (project_name, user_id))


    def update_projects(self, param, data):
        sql = f"""UPDATE projects SET {param} = ? 
                WHERE project_name = ? AND user_id = ?"""
        # data should be a tuple like (new_value, project_name, user_id)
        self.__executemany(sql, [data]) 


    def delete_project(self, user_id, project_id):
        sql = """DELETE FROM projects 
WHERE user_id = ? AND project_id = ? """
        self.__executemany(sql, [(user_id, project_id)])
    
    def delete_skill(self, project_id, skill_id):
        # remove the link between a project and a skill
        sql = """DELETE FROM project_skills 
WHERE skill_id = ? AND project_id = ? """
        self.__executemany(sql, [(skill_id, project_id)])


if __name__ == '__main__':
    manager = DB_Manager(db)
    # Ensure tables exist before inserting default rows
    manager.create_tables()
    manager.default_insert()