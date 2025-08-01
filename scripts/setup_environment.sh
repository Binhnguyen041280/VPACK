# scripts/setup_environment.sh
#!/bin/bash
# Setup script for V_track ZaloPay integration

echo "🚀 Setting up V_track with ZaloPay Integration..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/modules/payments
mkdir -p backend/modules/webhooks  
mkdir -p backend/modules/licensing
mkdir -p backend/templates/email
mkdir -p backend/keys
mkdir -p environment
mkdir -p logs

# Set up Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv vtrack_env
source vtrack_env/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment files
echo "⚙️ Creating environment configuration..."
if [ ! -f environment/.env.development ]; then
    cp environment/.env.development.example environment/.env.development
    echo "✅ Created development environment file"
fi

# Set permissions for key directory
echo "🔒 Setting security permissions..."
chmod 700 backend/keys
chmod 600 environment/.env.*

# Initialize database
echo "🗄️ Initializing database..."
python -c "
from backend.modules.licensing.license_models import init_license_db
init_license_db()
print('Database initialized successfully')
"

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Update environment/.env.development with your credentials"
echo "2. Register ZaloPay merchant account"
echo "3. Configure SMTP email settings"
echo "4. Run: python backend/app.py"
echo ""
echo "📚 Documentation:"
echo "- ZaloPay: https://docs.zalopay.vn/"
echo "- V_track API: http://localhost:5000/health"