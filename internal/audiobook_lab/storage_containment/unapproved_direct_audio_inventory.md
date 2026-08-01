# Unapproved Direct Audio Inventory

- Audit: `P0_UNAPPROVED_AUDIO_STORAGE_CONTAINMENT_DRY_RUN`
- Generated: `2026-07-13T09:47:01Z`
- Git: `sprint/luxury-ux-rebirth` at `b3abe331359245163ddb7863c15416e04cbca05e`
- Inventory SHA-256: `21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c`
- Mutation performed: **No**

## Executive Summary

- Found **264** real direct audio objects across **146** slugs.
- **214** stale or unapproved audio objects are directly reachable.
- **392** stale or unapproved sidecars are directly reachable.
- A future atomic containment run has **606** reachable targets, subject to owner review and retention approval.
- The exact two current approved audio objects and eight approved sidecars are excluded from containment.

## Provider Breakdown

| Provider | Direct | Reachable direct | Approved current | Reachable stale/unapproved | Inaccessible stale/unapproved | Sidecars | Reachable stale/unapproved sidecars |
|---|---:|---:|---:|---:|---:|---:|---:|
| B2 | 6 | 5 | 2 | 3 | 1 | 8 | 0 |
| Cloudinary | 258 | 211 | 0 | 211 | 47 | 564 | 392 |

## Approved Controls

| Slug | Manifest | Enabled | Gate | QA | Proxy range | Content-Range | Result |
|---|---:|---|---|---|---:|---|---|
| a-ghost-story | 200 | true | APPROVED | QA_PASSED | 206 | bytes 0-1023/7047789 | PASS |
| book-2b9853ec52 | 200 | true | APPROVED | QA_PASSED | 206 | bytes 0-1023/5233965 | PASS |

## Hidden API Controls

| Slug | Manifest | Enabled | Provider/voice/URL/assets empty | Audio proxy | Result |
|---|---:|---|---|---:|---|
| bn-066 | 200 | false | true | 404 | PASS |
| book-d19e96859f | 200 | false | true | 404 | PASS |
| book-f5d593e1f4 | 200 | false | true | 404 | PASS |
| muchiram-gurer-jibanchorit | 200 | false | true | 404 | PASS |
| the-open-window | 200 | false | true | 404 | PASS |
| dsires-baby | 200 | false | true | 404 | PASS |

## Sampled P0 Slugs

| Slug | Provider | HTTP | Range | Bypass | Recommendation |
|---|---|---:|---:|---|---|
| alices-adventures-in-wonderland | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| bn-027 | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| lokrahasya | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| mrinalini | B2 | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| nishkriti | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| the-wonderful-wizard-of-oz | B2 | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| bn-059 | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| bn-066 | B2 | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |
| the-art-of-money-getting | Cloudinary | 200 | 206 | true | MOVE_TO_PRIVATE_QA_BUCKET |

## Per-Slug Containment Matrix

| Slug | Title | Approved | API audio | Direct bypass | Sidecar bypass | Recommendation | Risk |
|---|---|---|---|---:|---:|---|---|
| a-ghost-story | A Ghost Story | true | true | 3 | 0 | MOVE_STALE_OBJECTS_TO_PRIVATE_QA_BUCKET_AND_RETAIN_APPROVED_PUBLIC | P0_CRITICAL |
| a-horseman-in-the-sky | A Horseman in the Sky | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-jury-of-her-peers | A Jury of Her Peers | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-mystery-of-heroism | A Mystery of Heroism | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-retrieved-reformation | A Retrieved Reformation | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-scandal-in-bohemia | A Scandal in Bohemia | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-wagner-matinee | A Wagner Matinee | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| a-white-heron | A White Heron | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| acres-of-diamonds | Acres of Diamonds | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| alices-adventures-in-wonderland | Alice's Adventures in Wonderland | false | false | 2 | 8 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| an-occurrence-at-owl-creek-bridge | An Occurrence at Owl Creek Bridge | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| berenice | Berenice | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bharat-at-the-crossroads | Bharat at the Crossroads | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-027 | অপরিচিতা | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-031 | মহেশ | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-035 | বড়দিদি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-036 | মেজদিদি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-041 | আঁধারে আলো | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-059 | কমলাকান্তের দপ্তর | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-060 | ইন্দিরা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| bn-066 | আনন্দমঠ | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-0986aeb7e3 | হৈমন্তী | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-0deb35c750 | খাতা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-0fbdaa730e | গুপ্তধন | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-1090573dff | ছুটি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-2b9853ec52 | দুই বিঘা জমি | true | true | 1 | 0 | MOVE_STALE_OBJECTS_TO_PRIVATE_QA_BUCKET_AND_RETAIN_APPROVED_PUBLIC | P0_CRITICAL |
| book-2ddbed8293 | ব্যবধান | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-2e468c4990 | কাবুলিওয়ালা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-4968248842 | বলাই | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-4b944e64fa | একরাত্রি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-5461971092 | মেঘ ও রৌদ্র | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-5704b31005 | বিচারক | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-5aedda79fe | শাস্তি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-63afd5e9be | দেনাপাওনা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-754da4eab8 | তারাপ্রসন্নের কীর্তি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-827fdc7aee | রাসমণির ছেলে | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-88ded9b47c | মানভঞ্জন | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-95624627d5 | মধ্যবর্তিনী | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-9a7f771921 | কর্মফল | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-a23625bf36 | সমাপ্তি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-a4a369483f | সম্পত্তি সমর্পণ | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-a74c1a1451 | দালিয়া | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-ac5a71075e | পোস্টমাস্টার | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-b9d47814a8 | নিশীথে | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-bfc51280b3 | অতিথি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-c307a57868 | স্ত্রীর পত্র | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-c7f3ce526c | খোকাবাবুর প্রত্যাবর্তন | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-c85323409f | জীবিত ও মৃত | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-d19e96859f | গিন্নি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-d2fe532e1c | স্বর্ণমৃগ | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-edfcf810c5 | ক্ষুধিত পাষাণ | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-ef193ffc52 | দিদি | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-f5d593e1f4 | রামকানাইয়ের নির্বুদ্ধিতা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| book-fbdf2991ab | সুভা | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| boule-de-suif | Boule de Suif | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| dracula | Dracula | false | false | 0 | 0 | REVOKE_PUBLIC_DELIVERY | P1_HIGH |
| dsires-baby | Désirée's Baby | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| feathertop | Feathertop | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| jane-eyre | Jane Eyre | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| lokrahasya | লোকরহস্য | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| love-of-life | Love of Life | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| markheim | Markheim | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| mrinalini | মৃণালিনী | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| muchiram-gurer-jibanchorit | মুচিরাম গুড়ের জীবনচরিত | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| nishkriti | নিষ্কৃতি | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| pauls-case | Paul's Case | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| radharani | রাধারাণী | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| rappaccinis-daughter | Rappaccini's Daughter | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| rikki-tikki-tavi | Rikki-Tikki-Tavi | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| rip-van-winkle | Rip Van Winkle | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| sredni-vashtar | Sredni Vashtar | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-charles-augustus-milverton | The Adventure of Charles Augustus Milverton | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-abbey-grange | The Adventure of the Abbey Grange | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-beryl-coronet | The Adventure of the Beryl Coronet | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-blue-carbuncle | The Adventure of the Blue Carbuncle | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-copper-beeches | The Adventure of the Copper Beeches | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-dancing-men | The Adventure of the Dancing Men | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-empty-house | The Adventure of the Empty House | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-engineers-thumb | The Adventure of the Engineer's Thumb | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-final-problem | The Adventure of the Final Problem | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-greek-interpreter | The Adventure of the Greek Interpreter | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-noble-bachelor | The Adventure of the Noble Bachelor | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-priory-school | The Adventure of the Priory School | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-second-stain | The Adventure of the Second Stain | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventure-of-the-solitary-cyclist | The Adventure of the Solitary Cyclist | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-adventures-of-sherlock-holmes | The Adventures of Sherlock Holmes | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-ambitious-guest | The Ambitious Guest | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-art-of-money-getting | The Art of Money Getting | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-bet | The Bet | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-bishop | The Bishop | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-call-of-the-wild | The Call of the Wild | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-canterville-ghost | The Canterville Ghost | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-celebrated-jumping-frog-of-calaveras-county | The Celebrated Jumping Frog of Calaveras County | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-cop-and-the-anthem | The Cop and the Anthem | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-country-of-the-blind | The Country of the Blind | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-darling | The Darling | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-door-in-the-wall | The Door in the Wall | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-enchanted-april | The Enchanted April | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-fall-of-the-house-of-usher | The Fall of the House of Usher | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-five-orange-pips | The Five Orange Pips | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-furnished-room | The Furnished Room | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-gift-of-the-magi | The Gift of the Magi | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-great-gatsby | The Great Gatsby | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-happy-prince | The Happy Prince | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-imp-of-the-perverse | The Imp of the Perverse | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-lady-with-the-dog | The Lady with the Dog | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-last-leaf | The Last Leaf | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-legend-of-sleepy-hollow | The Legend of Sleepy Hollow | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-lifted-veil | The Lifted Veil | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-luck-of-roaring-camp | The Luck of Roaring Camp | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-man-in-a-case | The Man in a Case | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-man-who-would-be-king | The Man Who Would Be King | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-man-with-the-twisted-lip | The Man with the Twisted Lip | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-masque-of-the-red-death | The Masque of the Red Death | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-metamorphosis | The Metamorphosis | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-ministers-black-veil | The Minister's Black Veil | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-monkeys-paw | The Monkey's Paw | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-most-dangerous-game | The Most Dangerous Game | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-murders-in-the-rue-morgue | The Murders in the Rue Morgue | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-necklace | The Necklace | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-open-boat | The Open Boat | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-open-window | The Open Window | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-outcasts-of-poker-flat | The Outcasts of Poker Flat | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-pit-and-the-pendulum | The Pit and the Pendulum | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-principles-of-scientific-management | The Principles of Scientific Management | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-purloined-letter | The Purloined Letter | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-ransom-of-red-chief | The Ransom of Red Chief | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-red-headed-league | The Red-Headed League | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-science-of-getting-rich | The Science of Getting Rich | false | false | 2 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-selfish-giant | The Selfish Giant | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-speckled-band | The Speckled Band | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-stolen-white-elephant | The Stolen White Elephant | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-strange-case-of-dr-jekyll-and-mr-hyde | The Strange Case of Dr Jekyll and Mr Hyde | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-student | The Student | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-suicide-club | The Suicide Club | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-tell-tale-heart | The Tell-Tale Heart | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-time-machine | The Time Machine | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-withered-arm | The Withered Arm | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-wonderful-wizard-of-oz | The Wonderful Wizard of Oz | false | false | 2 | 8 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| the-yellow-wallpaper | The Yellow Wallpaper | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| to-build-a-fire | To Build a Fire | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| tobermory | Tobermory | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| ward-no-6 | Ward No. 6 | false | false | 1 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| white-fang | White Fang | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| young-goodman-brown | Young Goodman Brown | false | false | 2 | 4 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |
| yugalanguriya | যুগলাঙ্গুরীয় | false | false | 1 | 0 | MOVE_TO_PRIVATE_QA_BUCKET | P0_CRITICAL |

## Direct Object Detail

| Object | Slug | Provider | HTTP | Range | Bytes | Current approved | Bypass | Action | Primary source |
|---|---|---|---:|---:|---:|---|---|---|---|
| audio-db2d15bffed5f64f | a-ghost-story | B2 | 200 | 206 | 4594121 | true | false | RETAIN_APPROVED_PUBLIC | `data/controlled_publications/a-ghost-story/public_book.json` |
| audio-7e60f2c7f61c7a7e | a-ghost-story | Cloudinary | 200 | 206 | 4594121 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/metadata_book_rights_response.json` |
| audio-77023920a02496bd | a-ghost-story | Cloudinary | 200 | 206 | 4594121 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/auto_premium_qa.json` |
| audio-fa63599c4eab4a75 | a-ghost-story | Cloudinary | 200 | 206 | 8850329 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/rights_metadata_failure_diagnosis.json` |
| audio-f84c58005758e9b9 | a-horseman-in-the-sky | Cloudinary | 200 | 206 | 4987211 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-horseman-in-the-sky/public_book.json` |
| audio-380994839a11b488 | a-horseman-in-the-sky | Cloudinary | 200 | 206 | 9416455 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ac56caf30013a2e6 | a-jury-of-her-peers | Cloudinary | 200 | 206 | 15437654 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-jury-of-her-peers/public_book.json` |
| audio-bfbdd5e26cb4acf6 | a-mystery-of-heroism | Cloudinary | 200 | 206 | 6520390 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-mystery-of-heroism/public_book.json` |
| audio-c24846055586ae4b | a-retrieved-reformation | Cloudinary | 200 | 206 | 5634526 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-retrieved-reformation/public_book.json` |
| audio-6e6e147384d559e7 | a-scandal-in-bohemia | Cloudinary | 200 | 206 | 16328534 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-scandal-in-bohemia/public_book.json` |
| audio-e0b1f321c89f3873 | a-scandal-in-bohemia | Cloudinary | 200 | 206 | 31891374 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-bb4acf6a9d52e5d7 | a-wagner-matinee | Cloudinary | 200 | 206 | 6472429 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-wagner-matinee/public_book.json` |
| audio-193d865bb934f441 | a-wagner-matinee | Cloudinary | 200 | 206 | 11922538 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-af74a817f73f145b | a-white-heron | Cloudinary | 200 | 206 | 8027081 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/a-white-heron/public_book.json` |
| audio-e2f06bc734be48e8 | a-white-heron | Cloudinary | 200 | 206 | 14476269 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-84382398ca7a7f22 | acres-of-diamonds | Cloudinary | 200 | 206 | 83777742 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c333a50ccf9861b7 | alices-adventures-in-wonderland | Cloudinary | 200 | 206 | 49882454 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/alices-adventures-in-wonderland/public_book.json` |
| audio-a153540a1ffe5bdf | alices-adventures-in-wonderland | Cloudinary | 200 | 206 | 92078333 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/alices-adventures-in-wonderland/public_book.json` |
| audio-9f0795bd1671822a | an-occurrence-at-owl-creek-bridge | Cloudinary | 200 | 206 | 7460798 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/an-occurrence-at-owl-creek-bridge/public_book.json` |
| audio-e1bf73c5d0a9f288 | an-occurrence-at-owl-creek-bridge | Cloudinary | 200 | 206 | 14053921 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-6390b589317bf07c | berenice | Cloudinary | 200 | 206 | 6775084 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/berenice/public_book.json` |
| audio-6af2fa7c5838a4a0 | berenice | Cloudinary | 200 | 206 | 12701405 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-499d97e35288398e | bharat-at-the-crossroads | Cloudinary | 200 | 206 | 82189079 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/bharat-at-the-crossroads/public_book.json` |
| audio-f37a3fde0326761e | bn-027 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/bn-027/public_book.json` |
| audio-8bda199290c4ef06 | bn-027 | Cloudinary | 200 | 206 | 17008057 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/bn-027/public_book.json` |
| audio-1cedbceb0f4dd75c | bn-031 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/bn-031/public_book.json` |
| audio-d9437b7d70084650 | bn-031 | Cloudinary | 200 | 206 | 13921010 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ff50bf3ffdd0dd2b | bn-035 | Cloudinary | 404 | 404 |  | false | false | UNKNOWN_REQUIRES_OWNER_REVIEW | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-9b4ddde370651c46 | bn-035 | Cloudinary | 200 | 206 | 54192422 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-2e71c26eb9d67d99 | bn-036 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/bn-036/public_book.json` |
| audio-866c0028e4cef2f2 | bn-036 | Cloudinary | 200 | 206 | 34878528 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-71d9da2f0019bdf6 | bn-041 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/bn-041/public_book.json` |
| audio-8133b75d281e28e0 | bn-041 | Cloudinary | 200 | 206 | 22643400 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-312ca6774d62c895 | bn-059 | Cloudinary | 404 | 404 |  | false | false | UNKNOWN_REQUIRES_OWNER_REVIEW | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-242787c67e635295 | bn-059 | Cloudinary | 200 | 206 | 83247273 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/bn-059/public_book.json` |
| audio-d35fcec1a9959be2 | bn-060 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/bn-060/public_book.json` |
| audio-1c3456c504f47fe7 | bn-060 | Cloudinary | 200 | 206 | 26063978 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b6a71ac20e4149d9 | bn-066 | B2 | 200 | 206 | 156318450 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/bn-066/public_book.json` |
| audio-5c33345f05f8d4dc | bn-066 | Cloudinary | 404 | 404 |  | false | false | UNKNOWN_REQUIRES_OWNER_REVIEW | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-97be0407e8ada94f | book-0986aeb7e3 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-0986aeb7e3/public_book.json` |
| audio-299ac9e4bef59809 | book-0986aeb7e3 | Cloudinary | 200 | 206 | 16512148 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c1d6496989cccfed | book-0deb35c750 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-0deb35c750/public_book.json` |
| audio-1151f03bf159cedc | book-0deb35c750 | Cloudinary | 200 | 206 | 6811106 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-606ee0cc03a5a33a | book-0fbdaa730e | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-0fbdaa730e/public_book.json` |
| audio-1852358d6943eaf5 | book-0fbdaa730e | Cloudinary | 200 | 206 | 19758437 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-48dac5599074b11f | book-1090573dff | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-1090573dff/public_book.json` |
| audio-0500f600cc131d28 | book-1090573dff | Cloudinary | 200 | 206 | 7813999 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-75b4659201394da3 | book-2b9853ec52 | B2 | 200 | 206 | 5233965 | true | false | RETAIN_APPROVED_PUBLIC | `data/controlled_publications/book-2b9853ec52/public_book.json` |
| audio-570a4290b8cf94a3 | book-2b9853ec52 | Cloudinary | 404 | 404 |  | false | false | UNKNOWN_REQUIRES_OWNER_REVIEW | `internal/audiobook_lab/release_gate/book-2b9853ec52_20260705T161042Z/book_release_state.json` |
| audio-9d8ba02f4210cb0b | book-2b9853ec52 | Cloudinary | 200 | 206 | 2455345 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-a6f71b44b39e2ead | book-2ddbed8293 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-2ddbed8293/public_book.json` |
| audio-7390e2b7cb8811fe | book-2ddbed8293 | Cloudinary | 200 | 206 | 5653359 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-907e2eaa0fde4aa3 | book-2e468c4990 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-2e468c4990/public_book.json` |
| audio-c3708d9766f2ed18 | book-2e468c4990 | Cloudinary | 200 | 206 | 9707981 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-54cf58e4f9a3c650 | book-4968248842 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-4968248842/public_book.json` |
| audio-f1d1a7b58f015198 | book-4968248842 | Cloudinary | 200 | 206 | 5425990 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-479a1019c2cba965 | book-4b944e64fa | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-4b944e64fa/public_book.json` |
| audio-7f4fa03b523834ec | book-4b944e64fa | Cloudinary | 200 | 206 | 7867289 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-45a0210c022af711 | book-5461971092 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-5461971092/public_book.json` |
| audio-c05d1d872bc78960 | book-5461971092 | Cloudinary | 200 | 206 | 31715413 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-469a86fc07d9cb7b | book-5704b31005 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-5704b31005/public_book.json` |
| audio-ba3068b6b13f9eec | book-5704b31005 | Cloudinary | 200 | 206 | 8845941 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-8eaf5bbd2eb4626d | book-5aedda79fe | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-5aedda79fe/public_book.json` |
| audio-d6f2c4cce8d00b9d | book-5aedda79fe | Cloudinary | 200 | 206 | 12413222 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-a813999bdd17108b | book-63afd5e9be | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-63afd5e9be/public_book.json` |
| audio-1e0ae727036e07dc | book-63afd5e9be | Cloudinary | 200 | 206 | 8217539 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/book-63afd5e9be/go_live_evidence.json` |
| audio-aab527e344c676ac | book-754da4eab8 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-754da4eab8/public_book.json` |
| audio-87d0bf459f5c5d14 | book-754da4eab8 | Cloudinary | 200 | 206 | 8262470 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/book-754da4eab8/go_live_evidence.json` |
| audio-d795d05907afdeb0 | book-827fdc7aee | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-827fdc7aee/public_book.json` |
| audio-840d32eced2d7f9f | book-827fdc7aee | Cloudinary | 200 | 206 | 44010728 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-62c13607339ba4ba | book-88ded9b47c | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-88ded9b47c/public_book.json` |
| audio-57826d42f6dba8c7 | book-88ded9b47c | Cloudinary | 200 | 206 | 12816971 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c7e781f11b0f41bc | book-95624627d5 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-95624627d5/public_book.json` |
| audio-d8a9643145bb0c53 | book-95624627d5 | Cloudinary | 200 | 206 | 14783678 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-f7863909a3da57c5 | book-9a7f771921 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-9a7f771921/public_book.json` |
| audio-3496537f2dde4c28 | book-9a7f771921 | Cloudinary | 200 | 206 | 47478535 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c961e398d04ab6b4 | book-a23625bf36 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-a23625bf36/public_book.json` |
| audio-3e7b4b6bda715b23 | book-a23625bf36 | Cloudinary | 200 | 206 | 23314016 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-214d4f44b375bd10 | book-a4a369483f | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-a4a369483f/public_book.json` |
| audio-08cb4a680895f4a6 | book-a4a369483f | Cloudinary | 200 | 206 | 10100027 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ee51d6cf282e003f | book-a74c1a1451 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-a74c1a1451/public_book.json` |
| audio-46e145db3df8a2d4 | book-a74c1a1451 | Cloudinary | 200 | 206 | 9581340 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-4e29878de83dda04 | book-ac5a71075e | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-ac5a71075e/public_book.json` |
| audio-c63faeec734e63c6 | book-ac5a71075e | Cloudinary | 200 | 206 | 7335645 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-5b0761a5ca47f1ed | book-b9d47814a8 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-b9d47814a8/public_book.json` |
| audio-bd5dee95e2eb0a28 | book-b9d47814a8 | Cloudinary | 200 | 206 | 14937696 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-230148d46abf50c8 | book-bfc51280b3 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-bfc51280b3/public_book.json` |
| audio-68267a42d9dc041d | book-bfc51280b3 | Cloudinary | 200 | 206 | 21533092 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-493e1685bf77a121 | book-c307a57868 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-c307a57868/public_book.json` |
| audio-e67fda4fd3e54491 | book-c307a57868 | Cloudinary | 200 | 206 | 18440821 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-9a426a2bf2568ef1 | book-c7f3ce526c | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-c7f3ce526c/public_book.json` |
| audio-e765c65e97fc61bc | book-c7f3ce526c | Cloudinary | 200 | 206 | 9388661 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-e5d58ba5d27ee89b | book-c85323409f | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-c85323409f/public_book.json` |
| audio-4fda15e69b7341ae | book-c85323409f | Cloudinary | 200 | 206 | 14826101 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-89a3756941612d2f | book-d19e96859f | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-d19e96859f/public_book.json` |
| audio-5a74ff7f84dbe940 | book-d19e96859f | Cloudinary | 200 | 206 | 4173157 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-77838b0cfbd52d27 | book-d2fe532e1c | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-d2fe532e1c/public_book.json` |
| audio-dec4823c28ef8ff2 | book-d2fe532e1c | Cloudinary | 200 | 206 | 12900981 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-8d8dc399cf994c93 | book-edfcf810c5 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-edfcf810c5/public_book.json` |
| audio-6499085ee54c79d0 | book-edfcf810c5 | Cloudinary | 200 | 206 | 14079835 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b7231f1a3be502c6 | book-ef193ffc52 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-ef193ffc52/public_book.json` |
| audio-dc9a56ec772a99d2 | book-ef193ffc52 | Cloudinary | 200 | 206 | 12723348 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-4094b805503f990e | book-f5d593e1f4 | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-f5d593e1f4/public_book.json` |
| audio-118e7511e6404397 | book-f5d593e1f4 | Cloudinary | 200 | 206 | 6270267 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c52b93e16295bf4a | book-fbdf2991ab | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/book-fbdf2991ab/public_book.json` |
| audio-a263325a8fad2d64 | book-fbdf2991ab | Cloudinary | 200 | 206 | 7509307 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c12111af84beb84a | boule-de-suif | Cloudinary | 200 | 206 | 29325601 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/boule-de-suif/public_book.json` |
| audio-c733032917d98fb4 | dracula | B2 | 400 | 400 | 167 | false | false | UNKNOWN_REQUIRES_OWNER_REVIEW | `backend/tests/test_b2_audiobook_routing.py` |
| audio-53df33d0604d6b74 | dsires-baby | Cloudinary | 200 | 206 | 4248834 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/dsires-baby/public_book.json` |
| audio-118ace665e804f00 | dsires-baby | Cloudinary | 200 | 206 | 8203746 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-d4a98a9940826efc | feathertop | Cloudinary | 200 | 206 | 15579812 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/feathertop/public_book.json` |
| audio-37b167c09eafb2fb | feathertop | Cloudinary | 200 | 206 | 28523459 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-37b8c294986f8a0b | jane-eyre | Cloudinary | 200 | 206 | 62999580 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/jane-eyre/public_book.json` |
| audio-9571948ac13d20dd | lokrahasya | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/lokrahasya/public_book.json` |
| audio-17fd970d6f45ebdf | lokrahasya | Cloudinary | 200 | 206 | 94953892 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/lokrahasya/public_book.json` |
| audio-da9addacb5bb185f | love-of-life | Cloudinary | 200 | 206 | 15315401 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/love-of-life/public_book.json` |
| audio-197e28802c67c93d | markheim | Cloudinary | 200 | 206 | 13227068 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/markheim/public_book.json` |
| audio-766f170fef3e9dfe | markheim | Cloudinary | 200 | 206 | 24674473 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-9acbe327e46bf107 | mrinalini | B2 | 200 | 206 | 155956706 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/mrinalini/public_book.json` |
| audio-5c2ef248f83ff9ba | mrinalini | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/mrinalini/public_book.json` |
| audio-42ed59f8a813c9dd | muchiram-gurer-jibanchorit | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/muchiram-gurer-jibanchorit/public_book.json` |
| audio-006bc0245fc98a0b | muchiram-gurer-jibanchorit | Cloudinary | 200 | 206 | 4388197 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-77c0593fab0fc458 | nishkriti | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/nishkriti/public_book.json` |
| audio-372872d61358d6eb | nishkriti | Cloudinary | 200 | 206 | 59435511 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/nishkriti/public_book.json` |
| audio-d42c993c6015fa81 | pauls-case | Cloudinary | 200 | 206 | 16604857 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/pauls-case/public_book.json` |
| audio-e39462befdc33658 | radharani | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/radharani/public_book.json` |
| audio-920169fb79223b16 | radharani | Cloudinary | 200 | 206 | 28690434 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-e54f92e04c7da867 | rappaccinis-daughter | Cloudinary | 200 | 206 | 23292726 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/rappaccinis-daughter/public_book.json` |
| audio-62acd92c37357985 | rappaccinis-daughter | Cloudinary | 200 | 206 | 42154571 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0d9b1abfd6667462 | rikki-tikki-tavi | Cloudinary | 200 | 206 | 5475440 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/rikki-tikki-tavi/public_book.json` |
| audio-3580dc4b9531372f | rip-van-winkle | Cloudinary | 200 | 206 | 13616553 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/rip-van-winkle/public_book.json` |
| audio-ab10357d75cc53c7 | rip-van-winkle | Cloudinary | 200 | 206 | 24913964 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-8969bad2aa744566 | sredni-vashtar | Cloudinary | 200 | 206 | 3540393 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/sredni-vashtar/public_book.json` |
| audio-0a257b5c91873857 | sredni-vashtar | Cloudinary | 200 | 206 | 6493457 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-89f566f64a80909b | the-adventure-of-charles-augustus-milverton | Cloudinary | 200 | 206 | 12638999 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-charles-augustus-milverton/public_book.json` |
| audio-983c6a22d743b82b | the-adventure-of-charles-augustus-milverton | Cloudinary | 200 | 206 | 24406561 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-67ec3a266047f59c | the-adventure-of-the-abbey-grange | Cloudinary | 200 | 206 | 17301386 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-abbey-grange/public_book.json` |
| audio-7f0e4053ef0c7f80 | the-adventure-of-the-abbey-grange | Cloudinary | 200 | 206 | 32983710 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-07b65799646ea83d | the-adventure-of-the-beryl-coronet | Cloudinary | 200 | 206 | 17736952 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-beryl-coronet/public_book.json` |
| audio-4b3571b678ab3af3 | the-adventure-of-the-beryl-coronet | Cloudinary | 200 | 206 | 33572197 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-4d7c2096c9689d4f | the-adventure-of-the-blue-carbuncle | Cloudinary | 200 | 206 | 14827015 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-blue-carbuncle/public_book.json` |
| audio-a1753e4ab88ec857 | the-adventure-of-the-blue-carbuncle | Cloudinary | 200 | 206 | 28679776 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-696df009cad449e6 | the-adventure-of-the-copper-beeches | Cloudinary | 200 | 206 | 18673912 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-copper-beeches/public_book.json` |
| audio-2c6dcbe7bab6cfa5 | the-adventure-of-the-copper-beeches | Cloudinary | 200 | 206 | 34930355 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ddfb8b016825d609 | the-adventure-of-the-dancing-men | Cloudinary | 200 | 206 | 18223770 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-dancing-men/public_book.json` |
| audio-eddbfe5b4fae5ee4 | the-adventure-of-the-dancing-men | Cloudinary | 200 | 206 | 34543116 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0933a421562c0ef5 | the-adventure-of-the-empty-house | Cloudinary | 200 | 206 | 16889017 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-empty-house/public_book.json` |
| audio-c3498c976209bd05 | the-adventure-of-the-empty-house | Cloudinary | 200 | 206 | 31408213 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-cfcee68a625b0c84 | the-adventure-of-the-engineers-thumb | Cloudinary | 200 | 206 | 15554735 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-engineers-thumb/public_book.json` |
| audio-c8a903fa24e64ac6 | the-adventure-of-the-engineers-thumb | Cloudinary | 200 | 206 | 29126992 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-11b16f695d218fb6 | the-adventure-of-the-final-problem | Cloudinary | 200 | 206 | 13541164 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-final-problem/public_book.json` |
| audio-fee4eba2cf65d9b1 | the-adventure-of-the-final-problem | Cloudinary | 200 | 206 | 24995675 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-db939dfc5a78e3e5 | the-adventure-of-the-greek-interpreter | Cloudinary | 200 | 206 | 13417030 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-greek-interpreter/public_book.json` |
| audio-91569f3e683cae8f | the-adventure-of-the-greek-interpreter | Cloudinary | 200 | 206 | 25423456 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c391aeb9cae631fa | the-adventure-of-the-noble-bachelor | Cloudinary | 200 | 206 | 15478405 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-noble-bachelor/public_book.json` |
| audio-15f9ea039aff8519 | the-adventure-of-the-noble-bachelor | Cloudinary | 200 | 206 | 29421235 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-dbb994fc8ac0afe1 | the-adventure-of-the-priory-school | Cloudinary | 200 | 206 | 22244171 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-priory-school/public_book.json` |
| audio-229042c40a278df7 | the-adventure-of-the-priory-school | Cloudinary | 200 | 206 | 42994878 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-fe5d7220c366035b | the-adventure-of-the-second-stain | Cloudinary | 200 | 206 | 18801180 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-second-stain/public_book.json` |
| audio-0f6ca64420fa86e3 | the-adventure-of-the-second-stain | Cloudinary | 200 | 206 | 36697487 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-67715dffc787bcbf | the-adventure-of-the-solitary-cyclist | Cloudinary | 200 | 206 | 15181549 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-adventure-of-the-solitary-cyclist/public_book.json` |
| audio-c3ff1242d595f638 | the-adventure-of-the-solitary-cyclist | Cloudinary | 200 | 206 | 28692524 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-68dbb96735060dcc | the-adventures-of-sherlock-holmes | Cloudinary | 200 | 206 | 98436668 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-fb1ff6d6a9f9877f | the-ambitious-guest | Cloudinary | 200 | 206 | 6155668 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-ambitious-guest/public_book.json` |
| audio-c78490f369cce64f | the-ambitious-guest | Cloudinary | 200 | 206 | 11225382 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-dc3e9ab645a73403 | the-art-of-money-getting | Cloudinary | 200 | 206 | 26706251 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-72f8d97096a7bae3 | the-art-of-money-getting | Cloudinary | 200 | 206 | 43537598 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/the-art-of-money-getting/public_book.json` |
| audio-a41da912937a6be8 | the-bet | Cloudinary | 200 | 206 | 5253033 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-bet/public_book.json` |
| audio-aa3b5f8279b98a4d | the-bet | Cloudinary | 200 | 206 | 9829817 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-d3a3e9952f2e3ab8 | the-bishop | Cloudinary | 200 | 206 | 12292459 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-bishop/public_book.json` |
| audio-60beddfa8c1e09c3 | the-call-of-the-wild | Cloudinary | 200 | 206 | 61557935 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-call-of-the-wild/public_book.json` |
| audio-d7988457134d2dc6 | the-canterville-ghost | Cloudinary | 200 | 206 | 22438679 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-canterville-ghost/public_book.json` |
| audio-9d4cbdb4ec8b2813 | the-celebrated-jumping-frog-of-calaveras-county | Cloudinary | 200 | 206 | 4859316 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-celebrated-jumping-frog-of-calaveras-county/public_book.json` |
| audio-caf3ef9cba71be3f | the-celebrated-jumping-frog-of-calaveras-county | Cloudinary | 200 | 206 | 8975717 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-32dcc4f7b3ed64f5 | the-cop-and-the-anthem | Cloudinary | 200 | 206 | 4576410 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-cop-and-the-anthem/public_book.json` |
| audio-0ec8ff9b5e384d25 | the-cop-and-the-anthem | Cloudinary | 200 | 206 | 8760050 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-8d7cc82f69293cc0 | the-country-of-the-blind | Cloudinary | 200 | 206 | 18267655 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-country-of-the-blind/public_book.json` |
| audio-5ee4cce450f23f5a | the-darling | Cloudinary | 200 | 206 | 9580321 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-darling/public_book.json` |
| audio-3125b110b5c9af55 | the-door-in-the-wall | Cloudinary | 200 | 206 | 12764230 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-301d869b1da49f76 | the-enchanted-april | Cloudinary | 200 | 206 | 78429171 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-00999f727433c51c | the-fall-of-the-house-of-usher | Cloudinary | 200 | 206 | 14874819 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-fall-of-the-house-of-usher/public_book.json` |
| audio-d5dccd355b7d2fa7 | the-fall-of-the-house-of-usher | Cloudinary | 200 | 206 | 26593950 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b5f17d3f6fb7e419 | the-five-orange-pips | Cloudinary | 200 | 206 | 13844446 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-five-orange-pips/public_book.json` |
| audio-abb75be1d0dfa8f2 | the-five-orange-pips | Cloudinary | 200 | 206 | 26127717 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-287776f32ed33681 | the-furnished-room | Cloudinary | 200 | 206 | 4935175 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-furnished-room/public_book.json` |
| audio-036ed045aa2afdfd | the-furnished-room | Cloudinary | 200 | 206 | 9448429 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ef7939c6b9280824 | the-gift-of-the-magi | Cloudinary | 200 | 206 | 3913265 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-gift-of-the-magi/public_book.json` |
| audio-233bb2eb41ea12a4 | the-gift-of-the-magi | Cloudinary | 200 | 206 | 7827792 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-67c6b975eeec464f | the-great-gatsby | Cloudinary | 200 | 206 | 93920514 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-great-gatsby/public_book.json` |
| audio-ae4e8f3b0309df6d | the-happy-prince | Cloudinary | 200 | 206 | 10554271 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-happy-prince/public_book.json` |
| audio-785e60f79cd41132 | the-happy-prince | Cloudinary | 200 | 206 | 20168037 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0b94266e0ef46b58 | the-imp-of-the-perverse | Cloudinary | 200 | 206 | 5074826 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-imp-of-the-perverse/public_book.json` |
| audio-c8d3b6a1d382a67b | the-imp-of-the-perverse | Cloudinary | 200 | 206 | 9507361 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-e76236ddb6179f3d | the-lady-with-the-dog | Cloudinary | 200 | 206 | 12733667 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-lady-with-the-dog/public_book.json` |
| audio-c60d13469b978607 | the-last-leaf | Cloudinary | 200 | 206 | 4505879 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-last-leaf/public_book.json` |
| audio-1ba1b092815e955c | the-last-leaf | Cloudinary | 200 | 206 | 8966940 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-6379c1f8be0af848 | the-legend-of-sleepy-hollow | Cloudinary | 200 | 206 | 24475603 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-legend-of-sleepy-hollow/public_book.json` |
| audio-ff5867a6a058b27c | the-legend-of-sleepy-hollow | Cloudinary | 200 | 206 | 43103547 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-c99a32197fa83d52 | the-lifted-veil | Cloudinary | 200 | 206 | 34640788 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-lifted-veil/public_book.json` |
| audio-5fc35bc1ac281852 | the-luck-of-roaring-camp | Cloudinary | 200 | 206 | 8424717 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-luck-of-roaring-camp/public_book.json` |
| audio-79486e41ab4b53d1 | the-luck-of-roaring-camp | Cloudinary | 200 | 206 | 15914048 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-03b7b9964efffdbb | the-man-in-a-case | Cloudinary | 200 | 206 | 10415247 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-man-in-a-case/public_book.json` |
| audio-0524b6c74c7e6f0d | the-man-in-a-case | Cloudinary | 200 | 206 | 19084060 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-1f7714eeaef3c702 | the-man-who-would-be-king | Cloudinary | 200 | 206 | 26664873 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-man-who-would-be-king/public_book.json` |
| audio-4737a8fd367979ae | the-man-who-would-be-king | Cloudinary | 200 | 206 | 49352455 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-839b884f81d731a9 | the-man-with-the-twisted-lip | Cloudinary | 200 | 206 | 17290571 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-man-with-the-twisted-lip/public_book.json` |
| audio-d8419986d62fdede | the-man-with-the-twisted-lip | Cloudinary | 200 | 206 | 32619459 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-184bd15417c5839f | the-masque-of-the-red-death | Cloudinary | 200 | 206 | 4688161 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-masque-of-the-red-death/public_book.json` |
| audio-4d0c47e4c4b6d067 | the-masque-of-the-red-death | Cloudinary | 200 | 206 | 8654097 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-094851a657053bb6 | the-metamorphosis | Cloudinary | 200 | 206 | 40509092 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-metamorphosis/public_book.json` |
| audio-77638ec65a05d7a0 | the-metamorphosis | Cloudinary | 200 | 206 | 72754826 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-1eb2d0f0e438eb5f | the-ministers-black-veil | Cloudinary | 200 | 206 | 10234375 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-ministers-black-veil/public_book.json` |
| audio-9ae63c81f7133fcd | the-ministers-black-veil | Cloudinary | 200 | 206 | 18378754 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-a9ae5b339149aef9 | the-monkeys-paw | Cloudinary | 200 | 206 | 7727247 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-monkeys-paw/public_book.json` |
| audio-9d237c1e2118176b | the-monkeys-paw | Cloudinary | 200 | 206 | 14155694 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0d8a01965388ecb3 | the-most-dangerous-game | Cloudinary | 200 | 206 | 15083120 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-most-dangerous-game/public_book.json` |
| audio-3a65d9a867ecfc0b | the-most-dangerous-game | Cloudinary | 200 | 206 | 28927208 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-431e1c6ad77734d9 | the-murders-in-the-rue-morgue | Cloudinary | 200 | 206 | 28100406 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-murders-in-the-rue-morgue/public_book.json` |
| audio-07be6ccf3acf5978 | the-murders-in-the-rue-morgue | Cloudinary | 200 | 206 | 52827786 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-edf6d7c46eedc284 | the-necklace | Cloudinary | 200 | 206 | 5505690 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-necklace/public_book.json` |
| audio-46a889f4f14ca7c5 | the-open-boat | Cloudinary | 200 | 206 | 28411838 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-open-boat/public_book.json` |
| audio-f1f58109e2c04424 | the-open-window | Cloudinary | 200 | 206 | 2338081 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-open-window/public_book.json` |
| audio-3774f44b02cd2a43 | the-open-window | Cloudinary | 200 | 206 | 4322786 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-09003e0a5643eb60 | the-outcasts-of-poker-flat | Cloudinary | 200 | 206 | 8295410 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-outcasts-of-poker-flat/public_book.json` |
| audio-2f3343537d38fe84 | the-outcasts-of-poker-flat | Cloudinary | 200 | 206 | 15568187 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-d10800ec4f1ad3d2 | the-pit-and-the-pendulum | Cloudinary | 200 | 206 | 12368788 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-pit-and-the-pendulum/public_book.json` |
| audio-550c394313c449f1 | the-pit-and-the-pendulum | Cloudinary | 200 | 206 | 23821000 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-419ca87e6d3174b5 | the-principles-of-scientific-management | Cloudinary | 200 | 206 | 71996308 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0d2a9a6b266b4ac3 | the-purloined-letter | Cloudinary | 200 | 206 | 14593481 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-purloined-letter/public_book.json` |
| audio-5b1303ba76df4cce | the-purloined-letter | Cloudinary | 200 | 206 | 26985160 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ae4e3ffabdd1e9a1 | the-ransom-of-red-chief | Cloudinary | 200 | 206 | 7748093 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-ransom-of-red-chief/public_book.json` |
| audio-950550216273b357 | the-ransom-of-red-chief | Cloudinary | 200 | 206 | 14890884 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-2b6398925be77b29 | the-red-headed-league | Cloudinary | 200 | 206 | 17306245 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-red-headed-league/public_book.json` |
| audio-bd43e910657a4398 | the-red-headed-league | Cloudinary | 200 | 206 | 32478607 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ed6a56661c736321 | the-science-of-getting-rich | Cloudinary | 200 | 206 | 43713376 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-f1e89a2d0e335795 | the-science-of-getting-rich | Cloudinary | 200 | 206 | 80320305 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b9cc52fb43552b0e | the-selfish-giant | Cloudinary | 200 | 206 | 2968312 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-selfish-giant/public_book.json` |
| audio-5114bc1b4826b9b4 | the-selfish-giant | Cloudinary | 200 | 206 | 5777911 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-2a12d764d8086f98 | the-speckled-band | Cloudinary | 200 | 206 | 18456677 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-speckled-band/public_book.json` |
| audio-262ff52aa56003d9 | the-speckled-band | Cloudinary | 200 | 206 | 34534339 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-7c05c330c5d110af | the-stolen-white-elephant | Cloudinary | 200 | 206 | 14139263 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-stolen-white-elephant/public_book.json` |
| audio-36d5a43e1c51e9bb | the-strange-case-of-dr-jekyll-and-mr-hyde | Cloudinary | 200 | 206 | 50172570 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-strange-case-of-dr-jekyll-and-mr-hyde/public_book.json` |
| audio-5601fb86133ddfe8 | the-strange-case-of-dr-jekyll-and-mr-hyde | Cloudinary | 200 | 206 | 88882826 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b192cc34fd9a30aa | the-student | Cloudinary | 200 | 206 | 2919097 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-student/public_book.json` |
| audio-fc06ecec376f201d | the-student | Cloudinary | 200 | 206 | 5296004 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-076d15e0bfbd7e56 | the-suicide-club | Cloudinary | 200 | 206 | 54303469 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-suicide-club/public_book.json` |
| audio-2b116904d1b65ff5 | the-tell-tale-heart | Cloudinary | 200 | 206 | 4169213 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-tell-tale-heart/public_book.json` |
| audio-edb542da8bc888b2 | the-tell-tale-heart | Cloudinary | 200 | 206 | 8614182 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-ba9f7e43177e3777 | the-time-machine | Cloudinary | 200 | 206 | 63694228 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-time-machine/public_book.json` |
| audio-04ab6efefbc1d15c | the-withered-arm | Cloudinary | 200 | 206 | 20537957 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-withered-arm/public_book.json` |
| audio-e284df4139980e2e | the-withered-arm | Cloudinary | 200 | 206 | 39561343 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-f241e23d457fe0ee | the-wonderful-wizard-of-oz | B2 | 200 | 206 | 127143854 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `backend/data/controlled_publications/the-wonderful-wizard-of-oz/public_book.json` |
| audio-d36aa0d759826a1f | the-wonderful-wizard-of-oz | Cloudinary | 200 | 206 | 70156870 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-wonderful-wizard-of-oz/public_book.json` |
| audio-89b5a7131f0178bd | the-yellow-wallpaper | Cloudinary | 200 | 206 | 11018362 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/the-yellow-wallpaper/public_book.json` |
| audio-d7bd542e397b1318 | the-yellow-wallpaper | Cloudinary | 200 | 206 | 20146303 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-0c5e00664654349d | to-build-a-fire | Cloudinary | 200 | 206 | 13247757 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/to-build-a-fire/public_book.json` |
| audio-8714fb57f5ffab88 | to-build-a-fire | Cloudinary | 200 | 206 | 25331296 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-b618b7a25eda4bb9 | tobermory | Cloudinary | 200 | 206 | 5626532 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/tobermory/public_book.json` |
| audio-44c31d5fc7c500f6 | ward-no-6 | Cloudinary | 200 | 206 | 42738173 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/ward-no-6/public_book.json` |
| audio-60792fb29d85b951 | white-fang | Cloudinary | 200 | 206 | 92750908 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-325f4cae9800c2da | young-goodman-brown | Cloudinary | 200 | 206 | 10366973 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `data/controlled_publications/young-goodman-brown/public_book.json` |
| audio-d0ad4f39a462810c | young-goodman-brown | Cloudinary | 200 | 206 | 19109346 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |
| audio-8f6b582d507bf580 | yugalanguriya | Cloudinary | 404 | 404 |  | false | false | REVOKE_PUBLIC_DELIVERY | `data/controlled_publications/yugalanguriya/public_book.json` |
| audio-afcc90a86cabed90 | yugalanguriya | Cloudinary | 200 | 206 | 20613581 | false | true | MOVE_TO_PRIVATE_QA_BUCKET | `internal/audiobook_lab/release_gate/cover_cloudinary_slug_assignment.json` |

## Source Reference Classification

- `HISTORICAL_LEDGER_SAFE`: 411 references
- `PRIVATE_EVIDENCE_ONLY`: 263 references
- `PUBLIC_SOURCE_RISK`: 564 references
- `TEST_FIXTURE_SAFE`: 3 references

## Notes

- HTTP and range probes were read-only. Reachable means HEAD 200/206 or range 200/206.
- A stale object attached to an approved slug is still a bypass unless it is the exact manifest-bound approved asset URL.
- Sidecars must be contained with their MP3 package; leaving timestamps, VTT, chapter, or metadata files public leaves package evidence exposed.
- Historical ledgers should retain checksums/object IDs after public URLs are redacted; no evidence should be destroyed without an approved retention decision.
