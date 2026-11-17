# Synthetic irrigation evidence-checking case

This self-contained offline software demonstration evaluates a declared event-record profile. All records, measurements, calibration flags, timestamps and fault conditions are synthetic. It does not run the three assessed repositories, use MQTT, operate equipment, execute a crop/greenhouse model, perform HIL testing, or validate physical effects.

## Reproduce

Python 3 with the standard library is sufficient; the recorded run used Python 3.12.14. From this directory, run:

```sh
python3 run_case.py --output outputs
```

The evaluator (`verifier.py`) reads the profile and records, not the expected labels. `run_case.py` compares its outputs with separately stored expectations and checks 20 record-order permutations for every case. `expected.csv` declares the expected verdict and a required failed check for each negative fixture. These expectations and faults were constructed from the proposed rules; they are not independent field labels or an external benchmark. Source order and received order are distinct. Identical command retransmissions preserve the issued payload; conflicting reuse does not.

## Contents and interpretation

`profile.json`: illustrative thresholds and units; none is a universal greenhouse recommendation. Times are seconds from a common synthetic origin, with no measured clock error. Context age is evaluated at command time. Flow volume is trapezoidally integrated from L/min samples using elapsed seconds divided by 60. Pressure bounds apply only to the supplied samples, not to an unobserved continuous process. The verifier audits completed records offline; it is not a real-time safety controller. Each fixture is processed independently; cross-episode anti-replay history, authentication and authorization are not tested.

`cases/`: 16 fixtures. `check_definitions.csv`: eight evidence checks. `expected.csv`: separate case expectations. `Input_Manifest.json`: checksums of the inputs prepared before evaluator execution.

`outputs/results.csv`: case verdicts, the defined acknowledgement-only reference and failed checks. A blank integrated volume means the trace did not permit computation under the declared unit/quality/time profile. `check_results.csv`: all 128 case/check outcomes. `verdicts.json`: complete structured outputs. `execution_record.json`: actual execution time, environment, source/input hashes and aggregate counts.

The acknowledgement-only reference labels an episode verified when it contains a matched accepted acknowledgement. It intentionally omits the other checks and does not represent any assessed platform or a state-of-the-art method. Differences illustrate the information omitted by that defined rule; they are not a representative performance comparison.

The recorded run matched all 16 constructed expectations: three verified and 13 not verified. Twelve negative fixtures also met the acknowledgement-only rule. All 320 record-order permutations preserved the corresponding outputs. These are finite conformance outcomes, not an accuracy estimate, a real-world fault-detection rate, or independent validation of the framework. Repeated runs reproduce verdict/check CSVs; execution timestamps and environment metadata may differ.
