-- WanderLog Development Seed Data
-- To be executed AFTER server/schema.sql
-- Safe: only INSERT statements with ON CONFLICT DO NOTHING, plus sequence synchronization.

-- 1. USERS
INSERT INTO users (user_id, username, email, password_hash, display_name, bio, account_status)
OVERRIDING SYSTEM VALUE VALUES
(1, 'alex_traveler', 'alex@example.com', 'dev_hash_alex', 'Alex Mercer', 'Backpacker exploring hidden gems across the world.', 'active'),
(2, 'sarah_journeys', 'sarah@example.com', 'dev_hash_sarah', 'Sarah Jenkins', 'Documenting quiet mountain passes and coastal railways.', 'active'),
(3, 'dan_nomad', 'dan@example.com', 'dev_hash_dan', 'Dan Reynolds', 'Solo adventurer. Coffee, notebooks, and train tickets.', 'active'),
(4, 'priya_wander', 'priya@example.com', 'dev_hash_priya', 'Priya Sharma', 'Heritage trails and local culinary explorations.', 'active')
ON CONFLICT (user_id) DO NOTHING;

-- 2. POSTS
INSERT INTO posts (post_id, user_id, title, content, location, created_at)
OVERRIDING SYSTEM VALUE VALUES
(1, 1, 'Sunrise over the Sahyadri Ridges', 'Started the climb at 4:30 AM in pitch black mist. Reached the summit plateau just as the ridge line lit up in molten orange. The western breeze was chilling but the view was worth every single step.', 'Kalsubai Peak, MH', NOW() - INTERVAL '3 hours'),
(2, 2, 'The Heritage Narrow-Gauge Line', 'Rode the mountain train across 102 tunnels today. Watching pine valleys unfold outside the open carriage window feels like traveling back into the 1920s.', 'Shimla Railway', NOW() - INTERVAL '2 hours'),
(3, 3, 'Old Quarter Walking Notes', 'Cobblestone streets, morning bakeries opening before sunrise, and handwritten street signs. Sometimes getting lost without a map is the best itinerary.', 'Pondicherry French Quarter', NOW() - INTERVAL '1 hour')
ON CONFLICT (post_id) DO NOTHING;

-- 3. COMMENTS
INSERT INTO comments (comment_id, user_id, post_id, content, created_at)
OVERRIDING SYSTEM VALUE VALUES
(1, 2, 1, 'Did you take the eastern ladder route or the village trail? The ladder route can get slippery during dawn dew.', NOW() - INTERVAL '2 hours 30 minutes'),
(2, 4, 1, 'Incredible view! The cloud inversions this time of year are unmatched.', NOW() - INTERVAL '2 hours'),
(3, 1, 2, 'Such an iconic line! The slow pace makes you appreciate the landscape so much more.', NOW() - INTERVAL '1 hour 30 minutes')
ON CONFLICT (comment_id) DO NOTHING;

-- 4. REPLIES
INSERT INTO replies (reply_id, user_id, comment_id, content, created_at)
OVERRIDING SYSTEM VALUE VALUES
(1, 1, 1, 'Took the village trail going up and the ladder route down after the sun dried the mist!', NOW() - INTERVAL '2 hours 15 minutes'),
(2, 3, 1, 'Good call, the ladder steps have zero grip in the early morning.', NOW() - INTERVAL '2 hours 10 minutes')
ON CONFLICT (reply_id) DO NOTHING;

-- Synchronize sequences dynamically without hardcoding IDs
SELECT setval(pg_get_serial_sequence('users', 'user_id'), COALESCE(MAX(user_id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('posts', 'post_id'), COALESCE(MAX(post_id), 1)) FROM posts;
SELECT setval(pg_get_serial_sequence('comments', 'comment_id'), COALESCE(MAX(comment_id), 1)) FROM comments;
SELECT setval(pg_get_serial_sequence('replies', 'reply_id'), COALESCE(MAX(reply_id), 1)) FROM replies;
