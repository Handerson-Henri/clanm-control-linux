"""Codificação do protocolo Holtek, identificada no software público CL-MK043.

As constantes são identificadores públicos de protocolo do fabricante, não
senhas pessoais. Implementação independente; não executa nem distribui DLLs.
"""
_OFFSETS=bytes.fromhex('25f6e4764754e676')
_PERM=(5,4,7,6,1,0,3,2)
REFERENCE_ID=b'FB1512'
CLANM_ID=b'E5434D'
_MASK=(1<<64)-1

def encode(raw,protocol_id=CLANM_ID):
    if len(raw)!=8 or len(protocol_id)!=6:raise ValueError('Pacote/codificação inválidos.')
    permuted=bytearray(raw[index] for index in _PERM)
    for i,value in enumerate(protocol_id,1):permuted[i]^=value
    word=int.from_bytes(permuted,'big')
    rotated=((word<<3)|(word>>61))&_MASK
    return bytes((value+offset)&255 for value,offset in zip(rotated.to_bytes(8,'big'),_OFFSETS))

def decode(packet,protocol_id=CLANM_ID):
    if len(packet)!=8 or len(protocol_id)!=6:raise ValueError('Pacote/codificação inválidos.')
    adjusted=bytes((value-offset)&255 for value,offset in zip(packet,_OFFSETS))
    word=int.from_bytes(adjusted,'big');word=((word>>3)|(word<<61))&_MASK
    permuted=bytearray(word.to_bytes(8,'big'))
    for i,value in enumerate(protocol_id,1):permuted[i]^=value
    raw=bytearray(8)
    for i,index in enumerate(_PERM):raw[index]=permuted[i]
    return bytes(raw)

def translate_reference(packet):
    raw=decode(packet,REFERENCE_ID)
    if sum(raw)&255!=255:raise ValueError('Checksum do comando de referência inválido.')
    return encode(raw,CLANM_ID)
