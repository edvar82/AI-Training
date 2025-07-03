class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

    def verify_email(self):
        if "@" in self.email and "." in self.email.split("@")[-1]:
            return True
        return False

    def display_info(self):
        return f"User ID: {self.id}, Name: {self.name}, Email: {self.email}"