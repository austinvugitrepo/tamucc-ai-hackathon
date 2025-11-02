-- Create table
CREATE TABLE IF NOT EXISTS hospitals (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    eta VARCHAR(50),
    tags TEXT
);

-- Insert initial data
INSERT INTO hospitals (name, eta, tags) VALUES
('Saint Mary''s Medical Center', '6 min', 'Cardiology,ICU,24/7 ER'),
('Mercy Heart Institute', '10 min', 'Cardiac Surgery,Cath Lab'),
('Riverfront General', '7 min', 'Stroke Center,Neurology'),
('Metro Hospital', '12 min', 'CT Scan,Emergency Department');
