# Created by:
"""
```bash
export DEST=/tmp/aerich_temp
mkdir $DEST
cp tests/old_models.py $DEST/models.py
cd $DEST
createdb -h localhost -p 5432 -U postgres aerich_temp
echo 'TORTOISE_ORM = {
    "connections": {"default": "postgres://postgres:postgres@localhost:5432/aerich_temp"},
    "apps": {"models": {"models": ["models", "aerich.models"]}},
}' > settings.py
aerich init -t settings.TORTOISE_ORM
aerich init-db
dropdb -h localhost -p 5432 -U postgres aerich_temp
cd -
cat $DEST/migrations/models/0* > tests/tortoise_v1_models_state.py
python -c "f='tests/tortoise_v1_models_state.py';from pathlib import Path;p=Path(f);s=p.read_text('utf8');ss=s[s.index('MODELS_STATE'):];p.write_text(ss,encoding='utf8')"
```
"""

MODELS_STATE = (
    "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"
    "WPwBhwRL9wkHyU847PQZ4up/ZuJB7g=="
)
