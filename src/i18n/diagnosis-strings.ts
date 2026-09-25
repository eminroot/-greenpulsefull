// What the leaf model can say, in words a grower acts on. The server sends
// codes (leafnode/pi/weights/models.json lists them); this file owns the
// wording. Merged into each language table in translations.ts.
//
// Advice is one or two plain sentences: what to do today. It is general
// guidance for each disease, not a treatment plan, and the card says to confirm
// by eye because the model was trained on lab photos.

type Dict = Record<string, string>;

const en: Dict = {
  'disease.bacterial_spot': 'Bacterial spot',
  'disease.early_blight': 'Early blight',
  'disease.late_blight': 'Late blight',
  'disease.leaf_mold': 'Leaf mold',
  'disease.septoria_leaf_spot': 'Septoria leaf spot',
  'disease.spider_mites': 'Spider mites',
  'disease.target_spot': 'Target spot',
  'disease.yellow_leaf_curl_virus': 'Yellow leaf curl virus',
  'disease.mosaic_virus': 'Mosaic virus',
  'disease.healthy': 'Healthy leaf',

  'advice.bacterial_spot': 'Remove spotted leaves and water at the roots, not over the leaves. A copper spray slows it down.',
  'advice.early_blight': 'Pick off the lower spotted leaves and keep the foliage dry. Ask about a fungicide if it spreads.',
  'advice.late_blight': 'Act today. It can take a greenhouse in days: remove affected plants, bring the humidity down and call your agronomist.',
  'advice.leaf_mold': 'Ventilate and bring the humidity down. Remove the worst leaves.',
  'advice.septoria_leaf_spot': 'Remove the spotted lower leaves and avoid wetting the foliage. A fungicide helps if it keeps spreading.',
  'advice.spider_mites': 'Look under the leaves. Raise the humidity a little and treat with a miticide or predatory mites.',
  'advice.target_spot': 'Remove affected leaves, open up airflow between plants and keep the leaves dry.',
  'advice.yellow_leaf_curl_virus': 'There is no cure. Remove infected plants and control whiteflies, which carry it.',
  'advice.mosaic_virus': 'There is no cure. Remove infected plants and disinfect tools and hands, it spreads by touch.',
  'advice.healthy': 'Nothing to do. Your greenhouse keeps checking.',

  'crop.tomato': 'Tomato',
  'crop.pepper': 'Pepper',

  'diag.overline': 'Leaf check',
  'diag.sure': '{pct}% sure',
  'diag.uncertainTitle': 'Not sure yet',
  'diag.uncertainBody': 'Closest match: {disease} ({pct}%). A sharp daylight photo of one leaf will settle it.',
  'diag.alsoPossible': 'Also possible: {disease} {pct}%',
  'diag.caveat': 'Trained on lab photos. Confirm by eye before you treat.',
  'diag.lastRead': 'Last leaf the camera could read, {when}',
  'diag.latestUnreadable': 'The newest photo could not be read: {reason}',
  'diag.sensorsOnly': 'The stress score uses the sensors until the camera sees a leaf again.',

  'unreadable.too_dark': 'Photo too dark',
  'unreadable.overexposed': 'Photo too bright',
  'unreadable.no_leaf': 'No leaf in view',
  'unreadable.too_small': 'Photo too small',
  'unreadable.unknown': 'Photo not readable',
  'unreadableHint.too_dark': 'Normal at night.',
  'unreadableHint.overexposed': 'Direct sun may be hitting the lens.',
  'unreadableHint.no_leaf': 'Check the camera still points at a leaf.',
  'unreadableHint.too_small': 'Check the camera resolution.',
  'unreadableHint.unknown': 'Check the camera.',

  'scan.unreadable.too_dark': 'The photo is too dark to read the leaf. Retake it in daylight.',
  'scan.unreadable.overexposed': 'The photo is too bright. Retake it out of direct sun.',
  'scan.unreadable.no_leaf': 'No leaf in the middle of the photo. Fill the frame with one leaf and retake it.',
  'scan.unreadable.too_small': 'The photo is too small to read. Retake it closer.',

  'reason.disease': '{disease} spotted on a leaf. Check the plant.',
  'reason.alsoDisease': 'Also: {disease} spotted on a leaf.',
  'result.noLeafRead': 'No leaf read',
  'decision.notifiedLeaf': 'Farmer notified about the leaf.',
};

const tr: Dict = {
  'disease.bacterial_spot': 'Bakteriyel leke',
  'disease.early_blight': 'Erken yanıklık',
  'disease.late_blight': 'Mildiyö (geç yanıklık)',
  'disease.leaf_mold': 'Yaprak küfü',
  'disease.septoria_leaf_spot': 'Septorya yaprak lekesi',
  'disease.spider_mites': 'Kırmızı örümcek',
  'disease.target_spot': 'Hedef leke',
  'disease.yellow_leaf_curl_virus': 'Sarı yaprak kıvırcıklık virüsü',
  'disease.mosaic_virus': 'Mozaik virüsü',
  'disease.healthy': 'Sağlıklı yaprak',

  'advice.bacterial_spot': 'Lekeli yaprakları koparın, yaprakların üstünden değil kökten sulayın. Bakırlı ilaç yayılmayı yavaşlatır.',
  'advice.early_blight': 'Alttaki lekeli yaprakları toplayın ve yaprakları kuru tutun. Yayılırsa fungisit için danışın.',
  'advice.late_blight': 'Bugün müdahale edin. Birkaç günde serayı sarabilir: hastalıklı bitkileri çıkarın, nemi düşürün ve ziraat mühendisinizi arayın.',
  'advice.leaf_mold': 'Havalandırın ve nemi düşürün. En kötü yaprakları koparın.',
  'advice.septoria_leaf_spot': 'Lekeli alt yaprakları koparın, yaprakları ıslatmayın. Yayılmaya devam ederse fungisit işe yarar.',
  'advice.spider_mites': 'Yaprakların altına bakın. Nemi biraz artırın, akarisit ya da avcı akarla mücadele edin.',
  'advice.target_spot': 'Hastalıklı yaprakları koparın, bitkiler arasında hava akışını açın ve yaprakları kuru tutun.',
  'advice.yellow_leaf_curl_virus': 'Tedavisi yok. Hastalıklı bitkileri çıkarın ve virüsü taşıyan beyazsinekle mücadele edin.',
  'advice.mosaic_virus': 'Tedavisi yok. Hastalıklı bitkileri çıkarın, aletleri ve elleri dezenfekte edin; dokunmayla bulaşır.',
  'advice.healthy': 'Yapılacak bir şey yok. Seranız kontrol etmeye devam ediyor.',

  'crop.tomato': 'Domates',
  'crop.pepper': 'Biber',

  'diag.overline': 'Yaprak kontrolü',
  'diag.sure': '%{pct} emin',
  'diag.uncertainTitle': 'Henüz emin değil',
  'diag.uncertainBody': 'En yakın eşleşme: {disease} (%{pct}). Gün ışığında tek bir yaprağın net fotoğrafı bunu netleştirir.',
  'diag.alsoPossible': 'Diğer olasılık: {disease} %{pct}',
  'diag.caveat': 'Laboratuvar fotoğraflarıyla eğitildi. İlaçlamadan önce gözle doğrulayın.',
  'diag.lastRead': 'Kameranın okuyabildiği son yaprak, {when}',
  'diag.latestUnreadable': 'En yeni fotoğraf okunamadı: {reason}',
  'diag.sensorsOnly': 'Kamera tekrar yaprak görene kadar stres skoru sensörlerle hesaplanıyor.',

  'unreadable.too_dark': 'Fotoğraf çok karanlık',
  'unreadable.overexposed': 'Fotoğraf çok parlak',
  'unreadable.no_leaf': 'Kadrajda yaprak yok',
  'unreadable.too_small': 'Fotoğraf çok küçük',
  'unreadable.unknown': 'Fotoğraf okunamadı',
  'unreadableHint.too_dark': 'Gece bu normaldir.',
  'unreadableHint.overexposed': 'Objektife doğrudan güneş geliyor olabilir.',
  'unreadableHint.no_leaf': 'Kameranın hâlâ bir yaprağa baktığını kontrol edin.',
  'unreadableHint.too_small': 'Kamera çözünürlüğünü kontrol edin.',
  'unreadableHint.unknown': 'Kamerayı kontrol edin.',

  'scan.unreadable.too_dark': 'Fotoğraf yaprağı okumak için çok karanlık. Gün ışığında tekrar çekin.',
  'scan.unreadable.overexposed': 'Fotoğraf çok parlak. Doğrudan güneş almayan bir yerde tekrar çekin.',
  'scan.unreadable.no_leaf': 'Fotoğrafın ortasında yaprak yok. Tek bir yaprağı kadraja doldurup tekrar çekin.',
  'scan.unreadable.too_small': 'Fotoğraf okunamayacak kadar küçük. Daha yakından tekrar çekin.',

  'reason.disease': 'Yaprakta tespit edildi: {disease}. Bitkiyi kontrol edin.',
  'reason.alsoDisease': 'Ayrıca yaprakta tespit edildi: {disease}.',
  'result.noLeafRead': 'Yaprak okunamadı',
  'decision.notifiedLeaf': 'Üreticiye yaprak bulgusu bildirildi.',
};

const ru: Dict = {
  'disease.bacterial_spot': 'Бактериальная пятнистость',
  'disease.early_blight': 'Альтернариоз',
  'disease.late_blight': 'Фитофтороз',
  'disease.leaf_mold': 'Кладоспориоз',
  'disease.septoria_leaf_spot': 'Септориоз',
  'disease.spider_mites': 'Паутинный клещ',
  'disease.target_spot': 'Мишеневидная пятнистость',
  'disease.yellow_leaf_curl_virus': 'Вирус жёлтой курчавости листьев',
  'disease.mosaic_virus': 'Вирус мозаики',
  'disease.healthy': 'Здоровый лист',

  'advice.bacterial_spot': 'Удалите пятнистые листья и поливайте под корень, а не по листьям. Медьсодержащий препарат замедлит распространение.',
  'advice.early_blight': 'Оборвите нижние пятнистые листья и держите листву сухой. Если распространяется, спросите про фунгицид.',
  'advice.late_blight': 'Действуйте сегодня. За несколько дней может поразить всю теплицу: удалите больные растения, снизьте влажность и вызовите агронома.',
  'advice.leaf_mold': 'Проветрите и снизьте влажность. Удалите самые поражённые листья.',
  'advice.septoria_leaf_spot': 'Удалите нижние пятнистые листья и не мочите листву. Если продолжает распространяться, поможет фунгицид.',
  'advice.spider_mites': 'Осмотрите нижнюю сторону листьев. Немного повысьте влажность и обработайте акарицидом или выпустите хищных клещей.',
  'advice.target_spot': 'Удалите поражённые листья, улучшите проветривание между растениями и держите листья сухими.',
  'advice.yellow_leaf_curl_virus': 'Лечения нет. Удалите больные растения и боритесь с белокрылкой, которая переносит вирус.',
  'advice.mosaic_virus': 'Лечения нет. Удалите больные растения и дезинфицируйте инструменты и руки: вирус передаётся при касании.',
  'advice.healthy': 'Ничего делать не нужно. Теплица продолжает проверку.',

  'crop.tomato': 'Томат',
  'crop.pepper': 'Перец',

  'diag.overline': 'Проверка листа',
  'diag.sure': 'Уверенность {pct}%',
  'diag.uncertainTitle': 'Пока не уверен',
  'diag.uncertainBody': 'Ближе всего: {disease} ({pct}%). Чёткое фото одного листа при дневном свете прояснит.',
  'diag.alsoPossible': 'Также возможно: {disease} {pct}%',
  'diag.caveat': 'Обучена на лабораторных фото. Проверьте глазами перед обработкой.',
  'diag.lastRead': 'Последний распознанный лист, {when}',
  'diag.latestUnreadable': 'Последнее фото не распознано: {reason}',
  'diag.sensorsOnly': 'Пока камера не видит лист, индекс стресса считается по датчикам.',

  'unreadable.too_dark': 'Слишком тёмное фото',
  'unreadable.overexposed': 'Слишком светлое фото',
  'unreadable.no_leaf': 'В кадре нет листа',
  'unreadable.too_small': 'Слишком маленькое фото',
  'unreadable.unknown': 'Фото не распознано',
  'unreadableHint.too_dark': 'Ночью это нормально.',
  'unreadableHint.overexposed': 'Возможно, в объектив светит прямое солнце.',
  'unreadableHint.no_leaf': 'Проверьте, что камера всё ещё смотрит на лист.',
  'unreadableHint.too_small': 'Проверьте разрешение камеры.',
  'unreadableHint.unknown': 'Проверьте камеру.',

  'scan.unreadable.too_dark': 'Фото слишком тёмное, лист не разобрать. Переснимите при дневном свете.',
  'scan.unreadable.overexposed': 'Фото пересвечено. Переснимите не на прямом солнце.',
  'scan.unreadable.no_leaf': 'В центре фото нет листа. Снимите один лист крупным планом.',
  'scan.unreadable.too_small': 'Фото слишком маленькое. Снимите ближе.',

  'reason.disease': 'На листе признаки: {disease}. Осмотрите растение.',
  'reason.alsoDisease': 'Также на листе признаки: {disease}.',
  'result.noLeafRead': 'Лист не распознан',
  'decision.notifiedLeaf': 'Фермер уведомлён о находке на листе.',
};

export const diagnosisStrings = { en, tr, ru };
