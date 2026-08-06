# ADR 0010: Secret encryption library

- Status: approved
- Date: 2026-08-06
- Gate: G4 implementation
- Approved by: product owner

## Decision

Use PyCA `cryptography` for application-layer envelope encryption. Each value gets a fresh 256-bit DEK and AES-256-GCM ciphertext. The DEK is wrapped with a versioned 256-bit KEK using AES key-wrap-with-padding. Associated data binds the ciphertext to its tenant, object, and schema identity; the algorithm and key versions are persisted with the ciphertext.

Expose KEK access through a provider interface. Local deployments may load one root key from a separately mounted, permission-restricted file; production deployments can provide cloud KMS or Vault implementations without changing callers. This slice does not add a provider-specific integration or persist real credentials.

## Rationale

PyCA supplies audited, standard primitives and safe nonce handling without inventing a ciphertext format or cryptographic implementation. Fresh DEKs limit the impact of a compromised value, while versioned KEKs permit rotation and provider replacement.
