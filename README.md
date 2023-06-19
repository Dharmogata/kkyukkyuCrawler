# 뀨뀨 크롤러(kkyukkyuCrawler)
> 강의안에서 판례요지 따기를 손쉽게!

뀨뀨 크롤러는 PDF 강의안의 판례번호(예: 1234다12345)를 자동으로 인식해서 [casenote](https://casenote.kr/)로부터 해당 판례를 검색한 후, 
판례 정보를 긁어다가 txt 파일로 만들어주는 파이썬 라이브러리입니다.

판례를 찾아다니는 시간을 아껴 윤택한 로스쿨 생활을 해보아요!

## 설치
### 의존성
뀨뀨 크롤러의 요구사항은 다음과 같습니다:
- python (>=3.10)
- PyPDF2 (>=3.0.1)
- tqdm (>=4.65)
- beautifulsoup4 (>=4.12.2)

사실 파이썬3인 이상 버전은 조금 더 낮아도 될 것 같은데(시험해보지는 않음) 파이썬2는 안됩니다.

### 설치법
가장 쉬운 방법은 `pip`을 이용하는 방식입니다:

```commandline
    pip install kkyukkyuCrawler
```

아니면 git repo를 클론해서 가져다 써도 됩니다:

```commandline
    git clone https://github.com/eik4862/kkyukkyuCrawler.git
```

## 사용법 - 기초
`extract_and_export` 메소드에 입력할 PDF의 경로(`in.pdf`)와 출력할 txt의 경로(`out.txt`)를 넘겨주면 끝! 
당연히 PDF 경로가 유효하지 않으면 에러가 나고, 출력할 경로에 이미 해당 파일이 있는 경우에는 **경고 없이 덮어쓰기가 되니 주의해주세요.**

```python
    import kkyukkyuCrawler as kc
    kc.extract_and_export('in.pdf', 'out.txt')
```

## 사용법 - 심화
~~이 부분은 굳이 읽을 필요는 없는데~~ 혹시 호기심이 있는 분들이 있으실까봐... 뀨뀨 크롤러가 제공하는 클래스와 함수는 다음과 같습니다:
- `Case` 클래스
- `extract_id` 함수
- `search` 함수
- `export` 함수
- `extract_and_export` 함수

이하에서 각각에 대해 조금 더 자세히 살펴보도록 하겠습니다(개발자나 볼법한 디테일은 코드 주석에 있으니 참고 바랍니다).

### Case 클래스
#### 필드
|     필드      |      타입       | 설명                                         |
|:-----------:|:-------------:|--------------------------------------------|
|    `id`     | list of `str` | 판례 ID(예: 1234다12345)                       |
| `ref_pg_no` | list of `int` | 판례 ID가 등장한 PDF 면수                          |
|   `title`   |     `str`     | 판례제목(예: 대법원 2023. 6. 19. 선고 1234다12345 판결) |
|  `issues`   | list of `str` | 판시/결정사항                                    |
| `summaries` |    list of `str`   | 판결/결정요지                                    |
|  `results`  |    list of `str`     | 주문                                         |
|  `claims`   |   list of `str`     | 청구/항소/반소 등 취지                              |
|  `reasons`  |    list of `str`    | 이유                                         |
|    `src`    |     `str`     | 판례를 찾은 casenote URL                        |

#### 생성자
|    파라미터     |  타입   | 설명                                               |
|:-----------:|:-----:|--------------------------------------------------|
|    `_id`    | `str` | 판례 ID(예: 1234다12345)                      |
| `ref_pg_no` | `int` | 판례 ID가 등장한 PDF 면수     |

`Case` 클래스는 판례정보를 담기 위한 간단한 컨테이너입니다.
다음 예시는 강의안 10면에 있는 92다23285 판례를 casenote에서 검색하여 그 값을 stdout으로 출력하는 예시입니다.
이 예시는 이해를 돕기 위한 예시일 뿐, 현실적인 이용은 아님에 유의해주세요.

```python
    import kkyukkyuCrawler as kc
    case = kc.Case('92다23285', 10)  # 강의안 10면에 있는 92다23285 판례
    kc.search([case])  # casenote에서 92다23285를 검색(Case 객체의 내부정보가 업데이트됨)
    print(case)
    """
    >>> @title: 대법원 1992. 12. 11. 선고 92다23285 판결
    >>> @issues
    >>>   가. 이른바 실효의 원칙을 적용하기 위한 판단기준
    >>>   나. 근로자들이 면직 후 바로 아무런 이의 없이 퇴직금을 수령하였으며 그로부터 ...
    >>>   다. 위 "나"항의 경우 사용자의 보상규정에 해직자 중 복직희망자는 사용자측이 ...
    >>> @summaries
    >>>   가. 이른바 실효의 원칙이 적용되기 위하여 필요한 요건으로서의 실효기간 ...
    >>>   나. 근로자들이 면직 후 바로 아무런 이의 없이 퇴직금을 수령하였으며 그로부터 ...
    >>>   다. 위 “나”항의 경우 사용자의 보상규정에 해직자 중 복직희망자는 사용자측이 ...
    >>> @results
    >>>   원심판결 중 피고 패소부분을 파기하고 이 부분 사건을 서울고등법원에 환송한다.
    >>> @reasons
    >>>   피고 소송대리인의 상고이유에 대하여
    >>>   원심판결 이유에 의하면, 원심은 원고들이 1980.7. 경 국가보위비상대책위원회가 ...
    >>>   ...
    >>> @src: https://casenote.kr/%EB%8C%80%EB%B2%95%EC%9B%90/92%EB%8B%A423285
    """
```

### extract_id 함수
#### 입력

|    파라미터    |   타입    | 설명                                               |
|:----------:|:-------:|--------------------------------------------------|
|   `path`   |  `str`  | 읽을 PDF의 절대/상대경로                                  |
| `verbose`  | `bool`  | 만약 `True`이면 stdout으로 구체적인 리포트를 합니다(기본값: `False`) |

#### 출력
|       타입       | 설명 |
|:--------------:|---|
| list of `Case` | PDF에서 추출해낸 판례 ID(예: 1234다12345)를 담고 있는 `Case` 객체의 리스트 |

`extract_id` 함수는 PDF 파일을 입력받아 판례 ID를 추출합니다.
추출된 판례 ID는 `Case` 컨테이너에 담겨 리스트로 리턴됩니다.
다음 예시는 가상의 강의안 `in.pdf`에 있는 판례 ID를 추출하여 출력하는 예시입니다.

```python
    import kkyukkyuCrawler as kc
    cases = kc.extract_id('in.pdf')  # id.pdf에서 판례 ID 추출
    for case in cases:
        print(case.id)
    """
    >>> 2012두18325
    >>> 2008두14739
    >>> 96누9003
    >>> 97누19427
    >>> 2017다229048
    >>> 2017두63993
    """
```

> **주의** PDF 파싱의 미묘함으로 인해 판례 ID 추출은 100% 정확하지 않습니다.
> 가령, `1234다123453)`은 `1234다1234` + 각주 `53)`일수도 있고 `1234다123453` + 닫는괄호 `)`일수도 있습니다.
> 다른 예시로, `1234다(페이지 바뀜)1234`의 경우, PDF byte stream 상에서는 연속선상에 놓이지 않게 되어 파싱에 어려움이 있습니다.
> 따라서 일부 판례 ID가 추출되지 않을 수 있지만, 추출 정확도는 약 98% 이상이니 큰 걱정은 아닙니다.

### search 함수
#### 입력

|   파라미터    |       타입       | 설명                                               |
|:---------:|:--------------:|--------------------------------------------------|
|  `cases`  | list of `Case` | 검색할 판례 ID를 가진 `Case` 객체의 리스트                   |
| `verbose` |     `bool`     | 만약 `True`이면 stdout으로 구체적인 리포트를 합니다(기본값: `False`) |

`search` 함수는 입력된 `Case` 객체들의 판례 ID를 casenote에서 검색하여 그 정보를 해당하는 `Case` 객체에 채워넣는(fill-in) 함수입니다.
casenote 서버에 부담이 되지 않도록 0.5초에 하나의 판례를 검색하되, 검색해야 할 판례가 10개 이하이면 고속 모드로 전환하여 빠르게 검색을 마칩니다.
만약 casenote 서버에서 [429 에러](https://developer.mozilla.org/ko/docs/Web/HTTP/Status/429)를 응답하는 경우, 20초간 검색을 중단(timeout)한 후 재시도합니다.

다음 예시는 가상의 강의안 `in.pdf`에 있는 판례 ID를 추출하여 casenote에서 검색한 후, 판례 제목을 기준으로 오름차순 정렬하는 예시입니다.
이는 판례 색인을 만드는 경우에 유용하게 활용될 수 있는 예시입니다.

```python
    import kkyukkyuCrawler as kc
    cases = kc.extract_id('in.pdf')   # id.pdf에서 판례 ID 추출
    kc.search(cases)                  # casenote에서 검색
    cases.sort(key=lambda x: x.title) # 판례 제목을 key로 정렬
    for case in cases:
        print(case.title)
    """
    >>> 대법원 1998. 9. 8. 선고 96누9003 판결
    >>> 대법원 2000. 6. 9. 선고 97누19427 판결
    >>> 대법원 2010. 1. 14. 선고 2008두14739 판결
    >>> 대법원 2015. 9. 10. 선고 2012두18325 판결
    >>> 대법원 2017. 9. 7. 선고 2017다229048 판결
    >>> 대법원 2022. 5. 12. 선고 2017두63993 판결
    """
```

> **주의** 크롤링 자체는 문제되지 않지만, 이걸 아주 빠르게 많이 하면 그게 바로 DDOS이기 때문에 0.5초의 딜레이와 20초의 timeout을 두었습니다.
> 추가적인 개발시에도 이 조건은 지켜주셨으면 좋겠습니다.

### export 함수
#### 입력

|   파라미터    |       타입       | 설명                                                                           |
|:---------:|:--------------:|------------------------------------------------------------------------------|
|  `cases`  | list of `Case` | txt로 내보낼 판례 정보를 가진 `Case` 객체의 리스트                                            |
|  `path`   |     `str`      | 출력할 txt의 절대/상대경로                                                             |
| `simple`  |     `bool`     | 만약 `True`이면 판시사항과 판결요지만 내보냅니다. 만약 `False`이면 판결이유를 포함한 전문을 내보냅니다(기본값: `True`) |
| `verbose` |     `bool`     | 만약 `True`이면 stdout으로 구체적인 리포트를 합니다(기본값: `False`)                             |

`export` 함수는 말그대로 `Case` 객체들에 담긴 판례 정보를 txt 파일로 내보내는 함수입니다.
이때, `path` 상에 이미 파일이 존재하면 **경고 없이 덮어쓰게 되니 각별한 주의를 요합니다.**
다음 예시는 가상의 강의안 `in.pdf` 상의 판례 ID를 추출하여 casenote에 검색한 후, 판시사항과 판결요지만 `out.txt`로 저장하는 예시입니다.

```python
    import kkyukkyuCrawler as kc
    cases = kc.extract_id('in.pdf')   # id.pdf에서 판례 ID 추출
    kc.search(cases)                  # casenote에서 검색
    kc.export(cases, 'out.txt')       # out.txt로 내보내기
    with open('out.txt', 'r') as f:
        for line in f:
            print(line, end='')
    """
    >>> 대법원 2015. 9. 10. 선고 2012두18325 판결(7면)
    >>> [판시사항]
    >>>   거래상 지위 남용행위의 상대방이 경쟁자 또는 사업자가 아니라 일반 소비자인 경우, ...
    >>> [판결요지]
    >>>   거래상 지위 남용행위의 상대방이 경쟁자 또는 사업자가 아니라 일반 소비자인 경우에는 ...
    >>> [출처] https://casenote.kr/search/?q=2012%EB%91%9018325
    >>> 
    >>> 대법원 2010. 1. 14. 선고 2008두14739 판결(7면)
    >>> [판시사항]
    >>>   손해보험회사와 피보험자가 책임질 사고로 대물손해를 입은 피해차주 사이에 독점규제 ...
    >>> [판결요지]
    >>>   불공정거래행위에 관한 독점규제 및 공정거래에 관한 법률상의 관련 규정과 입법 취지 등에 ...
    >>> [출처] https://casenote.kr/search/?q=2008%EB%91%9014739
    >>> ...
    """
```

### extract_and_export 함수
#### 입력

|    파라미터    |   타입   | 설명                                                                           |
|:----------:|:------:|------------------------------------------------------------------------------|
| `path_in`  | `str`  | 읽을 PDF의 절대/상대경로                                            |
| `path_out` | `str`  | 출력할 txt의 절대/상대경로                                                             |
|  `simple`  | `bool` | 만약 `True`이면 판시사항과 판결요지만 내보냅니다. 만약 `False`이면 판결이유를 포함한 전문을 내보냅니다(기본값: `True`) |
| `verbose`  | `bool` | 만약 `True`이면 stdout으로 구체적인 리포트를 합니다(기본값: `False`)                             |

눈치채셨겠지만, `extract_and_export` 함수는 앞서 본 세 함수를 감싸는 wrapper입니다.
실제로 이 함수는 다음과 같이 구현되어 있습니다.

```python
    def extract_and_export(cls, path_in, path_out, simple=True, verbose=False):
        cases = cls.extract_id(path_in, verbose)
        cls.search(cases, verbose)
        cls.export(cases, path_out, simple, verbose)
```

## 개발
뀨뀨 크롤러는 각잡고 영리목적으로 만든 게 아닙니다. 따라서 자잘한 버그가 있을수도 있고, 엉성한 부분이 있을수도 있습니다. 
귀엽게 봐주시면 되겠습니다.

- 버그 리포트: lkd1962@naver.com

뀨뀨 크롤러는 MIT 라이선스로 자유롭게 활용이 가능합니다(영리목적도 가능). 
이 라이브러리 코드를 기초로 뭔가 다른 걸 해보고 싶다면 얼마든지 환영입니다! 
코드는 [github](https://github.com/eik4862/kkyukkyuCrawler.git)에 있습니다. 
docstring을 열심히 달아뒀으니 참고하시면 되겠습니다.