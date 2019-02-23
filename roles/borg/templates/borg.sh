{% for target in borg_repositories %}

export BORG_RSH="ssh -i /root/.ssh/id_ed25519"
export BORG_PASSPHRASE="{{ target.passphrase }}"
REPOSITORY="{{ target.repository }}"

borg init $REPOSITORY -e repokey|| true

{% if target.backup_mysql %}
mysqldump --all-databases | borg create --compression lzma,9 -v --stats $REPOSITORY::`hostname`-`date +%Y-%m-%d_%H-%M`-pgdumpall -
{% endif %}

{% if target.backup_postgresql %}
su postgres -c pg_dumpall | borg create --compression lzma,9 -v --stats $REPOSITORY::`hostname`-`date +%Y-%m-%d_%H-%M`-pgdumpall -
{% endif %}

borg create --compression lzma,9 -v --stats \
    $REPOSITORY::`hostname`-`date +%Y-%m-%d_%H-%M` \
    / \
{% for path in target.excluded_paths %}
    --exclude="{{ path }}" \
{% endfor %}
    --exclude=/var/log \
    --exclude=/var/cache \
    --exclude=/dev \
    --exclude=/proc \
    --exclude=/run \
    --exclude=/sys \
    --exclude=/tmp \
    --exclude=/boot

{% endfor %}
