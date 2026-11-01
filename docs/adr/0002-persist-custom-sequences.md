# Persist custom chord sequences in SQLite and match them at runtime

The app shipped with six "famous sequence" presets hardcoded in `main.py` and a
`SEQ_FAMOSA` tag precomputed into the CSV at scrape time. The frontend hardcoded
four of those six. There was no way for a visitor to add a sequence, and no code
path that compared a user-supplied sequence against a song's chords: the runtime
check was a membership test against the precomputed tag. The custom-sequences
feature requires an anonymous catalog that survives container restarts and grows
without a new deploy.

We are introducing a single SQLite database, created with the `sqlite3` module
already present in the `python:3.9-slim` image, holding only the sequence
catalog. Songs and genres stay in `data/top/dataset_final.csv`, loaded into
memory at startup as before, because the task explicitly keeps that boundary.
The database lives at `/app/instance/sequences.db`, outside `/app/data` — a bind
mount over `/app/data` would hide the 15.8 MB CSV that `Dockerfile:8` copies
into the image. The `Dockerfile` declares `VOLUME /app/instance`, and the README
and AGENTS.md document `docker run -p 8080:8080 -v ciframe-data:/app/instance
ciframe`; without the named volume the file survives `docker restart` but is
lost when the container is recreated. We chose SQLite over Postgres or Redis
because a second service contradicts ADR 0001's single-container, local-only
deploy, over in-memory state because that fails the persistence requirement, and
over `shelve`/JSON files because SQLite is transactional, already available, and
inspectable with SQL without adding a dependency.

For matching, we are replacing the tag lookup with a runtime function that
implements the tag's exact semantics: the catalog sequence must appear as a
contiguous block of tokens in the song's ordered chord list, and every chord in
the song must belong to the sequence's vocabulary, comparing only lowercased
strings. The research validated this definition against all 67,585 loaded songs:
it reproduces the six original result sets exactly (199, 296, 4, 5, 7, 3 songs)
with zero extra and zero missing IDs, which is the feature's regression
criterion. Looser definitions (contiguous without the closed vocabulary, ordered
subsequence, or set intersection) return thousands of additional songs and would
break that criterion; a dual-mode catalog would preserve the six but give the
same search two different meanings, which is why it was rejected. The
consequence we accept is that a user-created sequence can return very few or no
songs: a single passing chord outside the sequence disqualifies a song. The UI
states the rule instead of hiding it.

Because matching no longer reads `SEQ_FAMOSA`, `Musica` drops `seqs_famosas` and
the CSV loader stops splitting column 7. The column and
`scripts/generate_data_set.py` remain untouched: the tag is still the oracle for
the regression test in `scripts/validar_matching.py`, comparing sets of
`id_unico_musica` rather than counts. The six originals are seeded into the
catalog idempotently and keep their old keys (`BmGDA`, `CGAmF`, ...) so existing
`GET /similares?sequencia=` URLs keep working; new and old sequences are searched
through `sequencia_id`. Duplicate registration by canonical chord list returns
the existing row with HTTP 201 instead of creating a second entry, and result
ordering and pagination remain exactly as they are today.

This decision has deliberate limits. The catalog is open and anonymous: there is
no login, moderation, or rate limiting, and spam is an accepted risk for this
iteration. Matching scans the in-memory song list once per request, as the
sequence path already did, now comparing chord lists instead of tags; if latency
degrades as the catalog or traffic grows, a precomputed index can be added
without changing the semantics. If the product later needs higher recall for
custom sequences, loosening the closed-vocabulary condition is a new decision
that must be recorded separately, because it necessarily changes what the six
original sequences return.
