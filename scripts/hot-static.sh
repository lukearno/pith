while inotifywait -e modify tmpl/*.html tmpl/*/*.html; do
    make static
done
