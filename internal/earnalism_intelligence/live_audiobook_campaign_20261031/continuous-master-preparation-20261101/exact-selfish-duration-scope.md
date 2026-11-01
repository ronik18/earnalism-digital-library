Historical independent review captured before root applied the reviewed exact-master patch. Current source implementation and source-QA admission are recorded in CHECKPOINT.json and SOURCE-QA-ADMISSION.json; no production deployment is claimed.

# Candidate scope and validation

CANDIDATE NOT APPLIED. This is a routine in-scope implementation candidate for root review, not a new owner-approval gate or approval receipt. No owner12minute restriction was identified;720000ms is the existing implementationguard. Root retains integration authority.

Current Selfish package exposes six segment URLs after samebook authorization. Every segment GET checks same title lease/package, not ordered playbackposition. Therefore a valid samebook member can already retrieve the complete accepted story through those six URLs. Exactmaster-only singleclip changes physical response granularity and resourceadmission guard, not titlecontent entitlement, narrator, literary rights, territory, billableamountauthority or scopeofapprovedrecording. This correction supersedes any interpretation that newfullbookcontent itself wouldbe granted. Existing normal lease/wallet/media safeguards remain mandatory.

The perrequest guard extension still deserves concrete review: wholeclip777120ms/6217581bytes is one response ratherthan six, but streamed64KiBreads bound backendmemory; leaseauthorize occurs beforestream and does not periodicallyterminateadmittedbody. No20secondstreamlifetimeclaim. No general15minraise isneeded.

Patchexact-master-duration-exception.patch changes only backend/audiobook_packages.py shared duration helper and owner_produced_package.py matchingtopologycheck. Default720000 remains. Exception pins exactsource/manuscript/slug/duration/1652words/23paragraphs/onechapter/onesegment/order/start/end/hash/6217581bytes/MIME. Everywrongbinding restoresdefault andfailsnative777120validation. Native package digest,prefix/storageversions/replicas/sourceexpectation andallnormal topology checks stillrun; adoption, recordingrights, packageapproval, immutableprimaryDR andruntimeacceptance gates areoutsideandunchanged. It doesnot grantreleasefrom metadata flags.

Fresh local test command:

```sh
PYTHONDONTWRITEBYTECODE=1 python /tmp/earnalism-selfish-duration-review-20261101/candidate/test_exact_master_duration.py
```

Result7testmethodsPASS withsubcases for ordinary720000pass/720001fail, exact777120pass,777121/900000fail, incorrecttitle/source/manuscript/hash/bytes/MIME/wordparagraphbounds/chapter/topology/durationtypes, and retainedreplica/prefix/packagehash/expectedsource rejection. Tests execute copiedrealnativevalidator withonlycandidatepatch, plus AST-extracted actualownerproduced topologyvalidator toverify matchingbuilder/runtimepassanddeny. Syntheticfixturelocators are NOT actual derivative storage receipts oradoptionevidence; nothing here isrelease-ready.

Remaining review/tests: root/sourceowner inspectdiff; exactderivativeadoption/storagefullhash+prefixbinding; alignbuilder and runtime sharedhelper; routeownedstreamRange/lease regressions; currentruntimeacceptance after exactheadintegration. No ownerreapproval inferred for unchangedrights/voice/source, noallocation/synthesis/storagecalls/appwrites.

Currentaccepted6segmentaudio bytes sum6220878; unchangedfullmaster6217581,3297bytesless. No orderedpositionservergatefound in current package route.
