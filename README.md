# HTTP·DNS·SMTP 패킷 분석 실행 안내

외부 사이트에 직접 요청을 보내고, 그때 오가는 패킷을 캡처해 분석하는 프로그램입니다. 요청을 보내는 터미널과 캡처 프로그램은 같은 컴퓨터에서 실행하면 됩니다.

실행 환경은 유닉스 계열을 기준으로 합니다. 현재 코드는 macOS와 Linux를 지원하며, 사용하는 캡처 방식은 아래와 같습니다.

## 1. 분석할 내용

| 대상 | 기본 실험 대상 | 확인할 정보 |

| HTTP | http://example.com/ | 요청 메서드·경로·버전, 응답 상태 코드, Host·Content-Type·Content-Length 등 헤더 |
| DNS | 1.1.1.1에 example.com 조회 | 질의 이름·레코드 유형, 요청과 응답을 연결하는 Transaction ID, 응답 코드·반환 레코드 |
| SMTP | MailMock의 146.59.115.14:1125 | 연결 확인과 테스트 메일 전송. 명령·응답과 서버 오류를 단계별 확인 |

공통으로 출발지·목적지 IP와 포트, IP의 TTL을 확인합니다. TCP 패킷은 Seq·Ack와 플래그를 읽고, 연결 시작·데이터 전송·종료 관련 패킷을 구분해 보여줍니다. 전체 연결이 성공했는지는 패킷의 순서와 응답을 함께 보고 판단합니다.

기본 사이트와 서버 주소는 화면에서 바꿀 수 있습니다. 현재 분석 대상 포트는 HTTP 80·8080, DNS 53·1053, SMTP 25·2525·587·1125입니다.

## 2. 프로그램 실행

터미널에서 `packet_lab` 폴더로 이동합니다. VS Code에서 이 폴더를 열었다면 내장 터미널을 사용해도 됩니다.

macOS에서는 다음과 같이 실행합니다.

```sh
python3 app.py
```

Linux에서는 캡처 권한이 필요하므로 다음과 같이 실행합니다.

```sh
sudo python3 app.py --no-browser
```

실행한 컴퓨터의 브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8765/
```

기존 프로그램이 켜져 있으면 그 터미널에서 Control+C로 종료하고 다시 실행합니다. 

### 캡처 시작

1. 인터넷에 연결된 인터페이스를 선택합니다. macOS는 보통 `en0`, Linux는 `ens…` 또는 `eth…` 형태입니다. 컴퓨터 설정에 따라 이름은 달라질 수 있습니다.
2. **캡처 시작**을 누릅니다.
3. HTTP·DNS·SMTP 버튼을 누르거나, 아래 터미널 명령으로 요청을 직접 보냅니다.
4. 패킷 목록에서 항목을 눌러 상세 정보를 확인합니다.

외부 서버 실험에서는 내부 통신용인 `lo`·`lo0` 대신 실제 인터넷 통신이 지나는 인터페이스를 선택합니다. 화면의 기본 선택값도 실제 연결과 맞는지 확인해야 합니다.

요청 결과가 정상이어도 캡처 인터페이스가 다르면 패킷 목록이 비어 있을 수 있습니다. 터미널 응답과 캡처 목록을 함께 확인하세요.

## 3. 터미널에서 요청 보내기

캡처 프로그램을 켜 둔 상태에서 새 터미널을 열어 실행합니다.

### HTTP

```sh
curl -4 -v --http1.0 http://example.com/
curl -4 -v --http1.1 http://example.com/
```

각각 HTTP/1.0과 1.1 요청을 보냅니다. 

캡처 목록에서 요청의 GET·경로·Host와 응답의 상태 코드·헤더를 확인합니다. 요청과 응답의 HTTP 버전은 각각 읽어야 합니다. 1.0으로 요청해도 서버가 1.1로 응답할 수 있습니다.

### DNS

```sh
dig @1.1.1.1 example.com A
dig @1.1.1.1 example.com AAAA
dig @1.1.1.1 example.com MX
```

외부 DNS 서버인 1.1.1.1에 도메인 정보를 물어봅니다. A는 IPv4 주소, AAAA는 IPv6 주소, MX는 메일 서버 정보를 조회합니다. AAAA를 물어볼 때도 위 명령의 DNS 서버 접속 자체는 IPv4를 사용합니다.

질의와 응답의 Transaction ID, 도메인, 유형을 맞춰 보고 응답 코드와 반환 레코드를 확인합니다. 응답의 `truncated`가 true면 UDP 응답이 잘린 상태입니다.

### SMTP 연결 확인

`packet_lab` 폴더에서 실행합니다.

```sh
python3 external.py smtp --host 146.59.115.14 --port 1125
```

외부 SMTP 서버와 연결한 뒤 서버 인사, EHLO, NOOP, QUIT 응답을 확인합니다. 이 단계는 메일을 보내기 전의 연결 확인입니다. MAIL FROM·RCPT TO·DATA 분석은 아래 메일 전송 시험에서 확인해야 합니다.

## 로그인 없이 공개 SMTP 서버로 시험하기

[MailMock 공식 안내](https://mailmock.app/#demo)

메일이 공개 테스트함에 표시되므로 가짜 주소와 짧은 테스트 문장만 보냅니다. 이름·학번·비밀번호·실제 메일 내용은 넣지 않습니다. 운영자가 테스트용으로 공개한 서버지만, 현재 접속과 실제 메일 수신 여부는 별도로 확인해야 합니다.

수정된 프로그램을 재시작하고 외부 인터페이스에서 캡처를 켠 뒤, 다른 터미널에서 아래 명령을 실행합니다. 발신·수신 주소는 테스트용 표기입니다.

```sh
printf 'From: sender@example.test\r\nTo: receiver@example.test\r\nSubject: Network class SMTP test\r\n\r\nSMTP packet capture test.\r\n' |
curl -4 -v --connect-timeout 10 --max-time 30 smtp://146.59.115.14:1125 \
  --mail-from sender@example.test \
  --mail-rcpt receiver@example.test \
  --upload-file -
```

캡처 화면의 SMTP 필터에서 EHLO, MAIL FROM, RCPT TO, DATA와 서버 응답을 확인합니다. 마지막 DATA 이후 250 응답이 오면 서버가 메시지를 접수한 것입니다. 네트워크에서 접속이 차단되거나 공개 서버가 중단돼 있으면 연결이 실패할 수 있습니다. Wireshark 표시 필터는 `tcp.port == 1125`입니다.

현재 코드는 SMTP 분석 포트에 `1125`를 포함합니다. 위 명령으로 메일 전송을 시도할 수 있고, 화면 기본 서버는 `146.59.115.14`, 포트는 `1125`입니다. **연결 확인**은 기본 명령·응답만 확인하고, **테스트 메일 보내기**는 가짜 주소와 고정 본문을 한 번 전송합니다. 터미널에서는 `python3 external.py smtp --mode public-send`로 같은 전송을 실행할 수 있습니다. 기본 `python3 external.py smtp`는 연결 확인만 합니다.

## 4. Wireshark와 비교

우리 프로그램과 같은 컴퓨터, 같은 인터페이스에서 Wireshark 캡처를 시작한 뒤 요청을 보냅니다. 또는 프로그램에서 **PCAP 저장**을 눌러 받은 파일을 Wireshark로 열어도 됩니다.

| 대상 | Wireshark 표시 필터 |
|---|---|
| HTTP | `tcp.port == 80` |
| DNS | `udp.port == 53` |
| SMTP | `tcp.port == 2525` 또는 실제 사용한 포트 |

서버 IP와 포트, 요청 경로 또는 질의 도메인으로 같은 패킷을 찾습니다. IP·포트·플래그·Seq/Ack와 응용 메시지를 비교하면 됩니다.

Wireshark는 Seq/Ack를 상대 번호로 표시할 수 있으므로 우리 프로그램의 원시 번호와 기준을 맞춰 비교합니다. SMTP가 자동으로 해석되지 않으면 **Decode As**에서 SMTP를 지정할 수 있습니다.

## 6. 파일별 역할

| 파일 | 역할 |
|---|---|
| app.py | 프로그램 실행, 캡처 제어, 결과 제공, PCAP 저장 |
| capture.py | 운영체제별 패킷 수집 |
| analyzer.py | 헤더·응용 메시지 분석, TCP 데이터 조립, STARTTLS 전환 확인 |
| external.py | 외부 HTTP·DNS·SMTP 서버로 실험 요청 전송 |
| ui.html | 대상 입력, 패킷 목록·상세 정보 화면 |
| verify.py | 분석 코드 검사. `python3 verify.py`로 실행 |
| traffic.py | 기존 로컬 테스트 서버. 외부 실험 화면에서는 사용하지 않음 |

외부 Python 패키지 설치 없이 표준 라이브러리로 실행하도록 작성했습니다. PCAP 저장은 파일 형식으로 내보내는 기능이며 libpcap 라이브러리를 사용하지 않습니다.


**확인한 내용**

- example.com에 HTTP/1.0·1.1 요청을 보내고 200 응답을 받음
- 1.1.1.1에 example.com A 레코드를 질의하고 실제 주소 응답을 받음
- Mailtrap 서버의 인사·EHLO·NOOP·QUIT 응답을 확인함
- 분석·클라이언트 코드 검사 23개 통과

**남은 작업**

- 실제 제출 환경에서 송신·수신 캡처와 Wireshark 비교
- MailMock 공개 서버의 실제 메일 접수 확인. 사용자 실행에서 451 응답이 관측돼 실패 단계와 서버 문구를 추가 확인해야 함
- Mailtrap을 선택할 경우 계정 인증·메일 전송 확인
- 최종 실험 대상과 분석할 패킷 선정

