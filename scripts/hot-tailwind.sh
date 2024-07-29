while inotifywait -e modify www/*.html www/*/*.html www/*/*.css www/*/*.js; do
    make tailwind  
done
