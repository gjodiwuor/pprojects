IF OBJECT_ID('Users', 'U') IS NOT NULL
    DROP TABLE Users;

CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),  -- Auto-incrementing ID  
    username VARCHAR(50) NOT NULL UNIQUE,   -- Must be unique
    password VARCHAR(255) NOT NULL,         -- Will store hashed password
    email VARCHAR(100) NOT NULL UNIQUE      -- Must be unique            
);

CREATE TABLE Categories (
    category_id INT PRIMARY KEY IDENTITY(1,1),  --Auto-increment ID
    category_name VARCHAR(50) NOT NULL,         --The category names eg. food, transport etc.
 );

 CREATE TABLE Expenses (
    expense_id INT PRIMARY KEY IDENTITY(1,1),  -- Auto-increment ID
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(user_id),  --Foreign key referencing to Users table
    category_id INT NOT NULL FOREIGN KEY REFERENCES Categories(category_id),  --Foreign key referencing to Categories
    amount DECIMAL(12,2) NOT NULL,  --up to 12 digits, 2 after the decimal
    description VARCHAR(255),  --the description of the money spent, optional
    date DATE NOT NULL   --the date
);

CREATE TABLE Income (
    income_id INT PRIMARY KEY IDENTITY(1,1),  -- Auto-increment ID
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(User_id),  --Foreign key referencing to Users table
    amount DECIMAL(12,2) NOT NULL,  --up to 12 digits, 2 after the decimal
    source VARCHAR(100) NOT NULL,   --Source of the income
    date DATE NOT NULL   --the date
);